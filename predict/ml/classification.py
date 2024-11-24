# Importing the libraries
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC, LinearSVC
from predict.ml.utils import stand_scale, postprocess


def decision_tree_classification(X_train, X_test, y_train, y_test, df):
    classifier = DecisionTreeClassifier(criterion = 'entropy', random_state = 0)
    classifier.fit(X_train, y_train)
    y_pred = postprocess(classifier.predict(X_test), df, 'MC_DECISION_TREE_signal', y_test)

    # print(f'addd-decision_tree_classification: {df.tail()}')
    # print(f'decision_tree_classification Accuracy={accuracy_score(y_test, y_pred, normalize=True)}')
    # print('addd-decision_tree_classification predicated={0}'.format('SELL' if y_pred[-1]<0 else 'BUY'))
    return classifier

def random_forest_classification(X_train, X_test, y_train, y_test, df):
    # Feature Scaling
    X_train, X_test = stand_scale(X_train, X_test)
    # Fitting Random Forest Classification to the Training set

    classifier = RandomForestClassifier(n_estimators=10, criterion='entropy', random_state=0)
    classifier.fit(X_train, y_train)

    # Predicting the Test set results
    y_pred = postprocess(classifier.predict(X_test), df, 'MC_RANDOM_FOREST_signal', y_test)

    # print(f'addd-random_forest_classification: {df.tail()}')
    # print(f'random_forest_classification Accuracy={accuracy_score(y_test, y_pred, normalize=True)}')
    # print('addd-random_forest_classification predicated={0}'.format('SELL' if y_pred[-1]<0 else 'BUY'))
    return classifier

def knn_classification(X_train, X_test, y_train, y_test, df):
    classifier = KNeighborsClassifier(n_neighbors=5, metric='minkowski', p=2)
    classifier.fit(X_train, y_train)
    y_pred = postprocess(classifier.predict(X_test), df, 'MC_KNN_signal', y_test)
    return classifier

def svr_classification(X_train, X_test, y_train, y_test, df):
    classifier = SVC(kernel='linear', random_state=0, gamma='auto')
    classifier.fit(X_train, y_train)
    y_pred = postprocess(classifier.predict(X_test), df, 'MC_SVC_signal', y_test)
    return classifier

def linear_svr_classification(X_train, X_test, y_train, y_test, df):
    classifier = LinearSVC()
    classifier.fit(X_train, y_train)
    y_pred = postprocess(classifier.predict(X_test), df, 'MC_LSVC_signal', y_test)
    return classifier