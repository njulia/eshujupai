# Importing the libraries
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.svm import SVR, LinearSVR
from predict.ml.utils import postprocess
import pickle


def linear_regression(X_train, X_test, y_train, y_test, df):
    # Fitting Simple Linear Regression to the Training set
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)

    # # save the model to disk
    # filename = 'linear_model.sav'
    # pickle.dump(regressor, open(filename, 'wb'))
    #
    # # load the model from disk
    # regressor = pickle.load(open(filename, 'rb'))
    # result = regressor.score(X_test, Y_test)

    # Predicting the Test set results
    y_pred = postprocess(regressor.predict(X_test), df, 'MR_LINEAR_signal', y_test)
    # print(f'addd-y_test={y_test}, y_pred={y_pred}')
    # print(f'linear_regression Accuracy={accuracy_score(y_test, y_pred, normalize=True)}')
    # print('addd-linear_regression predicated={0}'.format('SELL' if y_pred[-1]<0 else 'BUY'))
    return regressor

def polynomial_regression(X_train, X_test, y_train, y_test, df):
    poly_regressor = PolynomialFeatures(degree=4)
    X_train_poly = poly_regressor.fit_transform(X_train)
    poly_regressor.fit(X_train_poly, y_train)
    linear_regressor = LinearRegression()
    linear_regressor.fit(X_train_poly, y_train)

    X_test_poly = poly_regressor.fit_transform(X_test)
    y_pred = postprocess(linear_regressor.predict(X_test_poly), df, 'MR_POLYNOMIAL_signal', y_test)

    return linear_regressor

def logistic_regression(X_train, X_test, y_train, y_test, df):
    regressor = LogisticRegression(random_state=0)
    regressor.fit(X_train, y_train)
    y_pred = postprocess(regressor.predict(X_test), df, 'MR_LOGISTIC_signal', y_test)
    return regressor

def svr_regression(X_train, X_test, y_train, y_test, df):
    # regressor = SVR(kernal='rbf')
    regressor = SVR()
    regressor.fit(X_train, y_train)
    y_pred  = postprocess(regressor.predict(X_test), df, 'MR_SVR_signal', y_test)
    return regressor

def linear_svr_regression(X_train, X_test, y_train, y_test, df):
    # regressor = SVR(kernal='rbf')
    regressor = LinearSVR()
    regressor.fit(X_train, y_train)
    y_pred  = postprocess(regressor.predict(X_test), df, 'MR_LSVR_signal', y_test)
    return regressor
