# Importing the libraries
from sklearn.cluster import KMeans
from predict.ml.utils import postprocess


def k_means_cluster(X_train, X_test, y_train, y_test, df):
    classifier = KMeans(n_clusters=2)
    classifier.fit(X_train, y_train)
    y_pred = postprocess(classifier.predict(X_test), df, 'MC_K_MEANS_signal', y_test)

    # print(f'addd-decision_tree_classification: {df.tail()}')
    # print(f'decision_tree_classification Accuracy={accuracy_score(y_test, y_pred, normalize=True)}')
    # print('addd-decision_tree_classification predicated={0}'.format('SELL' if y_pred[-1]<0 else 'BUY'))
    return classifier
