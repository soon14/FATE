#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#  Copyright 2019 The FATE Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from federatedml.statistic import statics
from federatedml.model_base import ModelBase
from federatedml.param.statistics_param import StatisticsParam
from arch.api.utils import log_utils
from federatedml.statistic.data_overview import get_header
from federatedml.statistic.statics import MultivariateStatisticalSummary
from federatedml.util import consts

LOGGER = log_utils.getLogger()


class StatisticInnerParam(object):
    def __init__(self):
        self.col_name_maps = {}
        self.header = []
        self.static_indices = []
        self.static_names = []

    def set_header(self, header):
        self.header = header
        for idx, col_name in enumerate(self.header):
            self.col_name_maps[col_name] = idx

    def set_static_all(self):
        self.static_indices = [i for i in range(len(self.header))]
        self.static_names = self.header

    def add_static_indices(self, static_indices):
        if static_indices is None:
            return
        for idx in static_indices:
            if idx >= len(self.header):
                LOGGER.warning("Adding indices that out of header's bound")
                continue
            if idx not in self.static_indices:
                self.static_indices.append(idx)
                self.static_names.append(self.header[idx])

    def add_static_names(self, static_names):
        if static_names is None:
            return
        for col_name in static_names:
            idx = self.col_name_maps.get(col_name)
            if idx is None:
                LOGGER.warning(f"Adding col_name: {col_name} that is not exist in header")
                continue
            if idx not in self.static_indices:
                self.static_indices.append(idx)
                self.static_names.append(self.header[idx])


class DataStatistics(ModelBase):

    def __init__(self):
        super().__init__()
        self.model_param = StatisticsParam()
        self.inner_param = StatisticInnerParam()
        self.schema = None
        self.statistic_obj: MultivariateStatisticalSummary = None
        self._result_dict = {}

        self._numeric_statics = []
        self._quantile_statics = []

    def _init_model(self, model_param):
        self.model_param = model_param
        for stat_name in self.model_param.statistics:
            if stat_name in self.model_param.LEGAL_STAT:
                self._numeric_statics.append(stat_name)
            else:
                self._quantile_statics.append(stat_name)

    def _init_param(self, data_instances):
        if self.schema is None or len(self.schema) == 0:
            self.schema = data_instances.schema

        if self.inner_param is not None:
            return
        self.inner_param = StatisticInnerParam()
        # self.schema = data_instances.schema
        LOGGER.debug("In _init_params, schema is : {}".format(self.schema))
        header = get_header(data_instances)
        self.inner_param.set_header(header)

        if self.model_param.column_indexes == -1:
            self.inner_param.set_static_all()
        else:
            self.inner_param.add_static_indices(self.model_param.column_indexes)
            self.inner_param.add_static_names(self.model_param.column_names)
        return self

    def fit_local(self, data_instances):
        self._init_param(data_instances)

        self.statistic_obj = MultivariateStatisticalSummary(data_instances,
                                                            cols_index=self.inner_param.static_indices,
                                                            abnormal_list=self.model_param.abnormal_list)
        results = None
        for stat_name in self._numeric_statics:
            stat_res = self.statistic_obj.get_statics(stat_name)
            if results is None:
                results = stat_res
            else:
                for k, v in results.items():
                    results[k] = dict(**v, **stat_res[k])

        print(results)

        for query_point in self._quantile_statics:
            q = float(query_point[:-1]) / 100
            res = self.statistic_obj.get_quantile_point(q, error=self.model_param.quantile_error)
            for k, v in res.items():
                results[k][query_point] = v
        return results
