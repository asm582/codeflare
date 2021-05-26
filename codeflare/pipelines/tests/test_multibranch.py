import pytest
import ray
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.tree import DecisionTreeClassifier
import codeflare.pipelines.Datamodel as dm
import codeflare.pipelines.Runtime as rt
from codeflare.pipelines.Datamodel import Xy
from codeflare.pipelines.Datamodel import XYRef
from codeflare.pipelines.Runtime import ExecutionType

class FeatureUnion(dm.AndTransform):
    def __init__(self):
        pass

    def transform(self, xy_list):
        X_list = []
        y_list = []

        for xy in xy_list:
            X_list.append(xy.get_x())
        X_concat = np.concatenate(X_list, axis=0)

        return Xy(X_concat, None)

def test_multibranch():

    ray.shutdown()
    ray.init()

    ## prepare the data
    X = pd.DataFrame(np.random.randint(0,100,size=(10000, 4)), columns=list('ABCD'))
    y = pd.DataFrame(np.random.randint(0,2,size=(10000, 1)), columns=['Label'])

    numeric_features = X.select_dtypes(include=['int64']).columns
    numeric_transformer = Pipeline(steps=[
        ('scaler', StandardScaler())])

    ## set up preprocessor as StandardScaler
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    ## create two decision tree classifiers with different depth limit
    c_a = DecisionTreeClassifier(max_depth=3)
    c_b = DecisionTreeClassifier(max_depth=5)

    ## initialize codeflare pipeline by first creating the nodes
    pipeline = dm.Pipeline()
    node_a = dm.EstimatorNode('preprocess', preprocessor)
    node_b = dm.EstimatorNode('c_a', c_a)
    node_c = dm.EstimatorNode('c_b', c_b)

    node_d = dm.EstimatorNode('d', MinMaxScaler())
    node_e = dm.EstimatorNode('e', StandardScaler())
    node_f = dm.AndNode('f', FeatureUnion())

    ## codeflare nodes are then connected by edges
    pipeline.add_edge(node_a, node_b)
    pipeline.add_edge(node_a, node_c)

    pipeline.add_edge(node_a, node_d)
    pipeline.add_edge(node_a, node_e)
    pipeline.add_edge(node_d, node_f)
    pipeline.add_edge(node_e, node_f)

    pipeline_input = dm.PipelineInput()
    xy = dm.Xy(X_train, y_train)
    pipeline_input.add_xy_arg(node_a, xy)

    ## execute the codeflare pipeline
    pipeline_output = rt.execute_pipeline(pipeline, ExecutionType.FIT, pipeline_input)
    assert pipeline_output

    ## retrieve node b
    node_b_output = pipeline_output.get_xyrefs(node_b)
    assert node_b_output

    ray.shutdown()


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
