from predict.process import preprocess
from predict.ml.utils import set_train_test, plot, visualize
from predict.ml.regression import linear_regression, polynomial_regression, logistic_regression, svr_regression, linear_svr_regression
from predict.ml.classification import decision_tree_classification, random_forest_classification, knn_classification, svr_classification, linear_svr_classification
from predict.ml.clustering import k_means_cluster
from web.settings import BASE_DIR
import os
import pandas as pd
import logging
import traceback


log = logging.getLogger(__name__)

def cal_ml_indicators(df):
    '''
    Convert pandas Dataframe to a dict with ndarray, then calculate the techinical indicators
    {'open': ndarray, 'close': ndarray, 'high': ndarray, 'low': ndarray, 'volume': ndarray}
    :param df: pandas DataFrame
    :return: pandas DataFrame enriched with technical indicators
    '''
    try:
        X_train, X_test, y_train, y_test = set_train_test(df)
        path = os.path.join(BASE_DIR, 'documents/ml_indicator.csv')
        df.to_csv(path)

        # Remove 'date' index for adding _signal column
        df.reset_index(inplace=True)

        # Run machine learning methods
        linear_regression(X_train, X_test, y_train, y_test, df)
        polynomial_regression(X_train, X_test, y_train, y_test, df)
        logistic_regression(X_train, X_test, y_train, y_test, df)
        svr_regression(X_train, X_test, y_train, y_test, df)
        linear_svr_regression(X_train, X_test, y_train, y_test, df)
        decision_tree_classification(X_train,  X_test, y_train, y_test, df)
        random_forest_classification(X_train,  X_test, y_train, y_test, df)
        knn_classification(X_train,  X_test, y_train, y_test, df)
        svr_classification(X_train,  X_test, y_train, y_test, df)
        linear_svr_classification(X_train,  X_test, y_train, y_test, df)
        k_means_cluster(X_train, X_test, y_train, y_test, df)

        # Reset the index to 'date'
        df.set_index('date', inplace=True)

        # path = os.path.join(BASE_DIR, 'documents/ml_indicator.csv')
        # df.to_csv(path)
    except:
        log.error(traceback.print_exc())


if __name__ == "__main__":
    path = os.path.join(BASE_DIR, 'documents/gold.csv')
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'], format='%b %d %Y')
    # df.set_index('date', inplace=True)
    # df.sort_index(ascending=True, inplace=True)
    # df.reset_index(inplace=True)
    df.sort_values(['date'], ascending=[True], inplace=True)
    preprocess(df)
    print(f'addd-tail-{df.tail()}')

    X_train, X_test, y_train, y_test = set_train_test(df)
    # classifier = linear_regression(X_train, X_test, y_train, y_test, df)
    # classifier = polynomial_regression(X_train, X_test, y_train, y_test, df)
    # classifier = svr_regression(X_train, X_test, y_train, y_test, df)
    classifier = logistic_regression(X_train, X_test, y_train, y_test, df)

    # plot(X_train, X_test, y_train, y_test, y_pred, df)
    visualize(X_train, X_test, y_train, y_test, classifier)
