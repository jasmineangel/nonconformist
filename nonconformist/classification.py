#!/usr/bin/env python

"""
docstring
"""

# Authors: Henrik Linusson

from __future__ import division

import numpy as np

# -----------------------------------------------------------------------------
# Error functions
# -----------------------------------------------------------------------------
def inverse_probability(prediction, y):
	prob = np.zeros((y.size,), dtype=np.float32)
	for i, y_ in enumerate(y):
		prob[i] = prediction[i, y[i]]
	return 1 - prob

def margin(prediction, y):
	prob = np.zeros((y.size,), dtype=np.float32)
	for i, y_ in enumerate(y):
		prob[i] = prediction[i, y[i]]
		prediction[i, y[i]] = -np.inf
	return 0.5 - ((prob - prediction.max(axis=1)) / 2)

# -----------------------------------------------------------------------------
# Nonconformity functions
# -----------------------------------------------------------------------------
class PetClassifierNc(object):
	def __init__(self, model_class, err_func, model_params=None):
		self.last_x, self.last_y = None, None
		self.last_prediction = None
		self.clean = False
		self.err_func = err_func

		self.model_class = model_class
		self.model_params = model_params if model_params else {}

		self.model = self.model_class(**self.model_params)

	def fit(self, x, y, increment=False):
		# TODO: incremental
		self.model.fit(x, y)
		self.clean = False

	def underlying_predict(self, x):
		if (not self.clean or
			self.last_x is None or
		    not np.array_equal(self.last_x, x)):

			self.last_x = x
			self.last_prediction = self.model.predict_proba(x)
			self.clean = True

		return self.last_prediction.copy()

	def calc_nc(self, x, y):
		prediction = self.underlying_predict(x)
		return self.err_func(prediction, y)

# -----------------------------------------------------------------------------
# Conformal predictors
# -----------------------------------------------------------------------------
class IcpClassifier(object):
	def __init__(self, nc_function):
		self.cal_x, self.cal_y = None, None
		self.classes = None
		self.nc_function = nc_function
		self.last_p = None

	def fit(self, x, y, increment=False):
		self.__update_classes(y, increment)
		self.nc_function.fit(x, y, increment)

	def calibrate(self, x, y, condition=None, increment=False):
		# TODO: conditional
		if increment and self.cal_x is not None and self.cal_y is not None:
			self.cal_x = np.vstack([self.cal_x, x])
			self.cal_x = np.hstack([self.cal_y, y])
		else:
			self.cal_x, self.cal_y = x, y

		self.__update_classes(y, increment)

		self.cal_scores = self.nc_function.calc_nc(self.cal_x, self.cal_y)

	def __update_classes(self, y, increment):
		if self.classes is None or not increment:
			self.classes = np.unique(y)
		else:
			self.classes = np.unique(np.hstack([self.classes, y]))

	def predict(self, x, significance=None):
		p = np.zeros((x.shape[0], self.classes.size))
		for i, c in enumerate(self.classes):
			test_class = np.zeros((x.shape[0]))
			test_class.fill(c)

			# TODO: maybe calculate p-values using cython or similar
			# TODO: smoothed, modified, interpolated p-values

			test_nc_scores = self.nc_function.calc_nc(x, test_class)
			for j, nc in enumerate(test_nc_scores):
				n_cal = self.cal_scores.size
				n_greater_equal = np.sum(self.cal_scores >= nc)
				p[j, i] = (n_greater_equal + 1) / (n_cal + 1)

		if significance:
			return p > significance
		else:
			return p