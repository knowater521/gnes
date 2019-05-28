#  Tencent is pleased to support the open source community by making GNES available.
#
#  Copyright (C) 2019 THL A29 Limited, a Tencent company. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# pylint: disable=low-comment-ratio


import numpy as np

from .base import BaseEncoder
from ..helper import batching, train_required


class HashEncoder(BaseEncoder):
    def __init__(self, num_bytes: int, cluster_per_byte: int = 8, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert 1 <= cluster_per_byte <= 8, 'maximum 8 hash functions in a byte'
        self.num_bytes = num_bytes
        self.num_clusters = cluster_per_byte
        self.x = None
        self.vec_dim = None
        self.matrixs = None
        self.mean = None
        self.var = None

    def train(self, vecs: np.ndarray, *args, **kwargs):
        print('num_bytes', self.num_bytes)
        self.vec_dim = vecs.shape[1]
        if self.vec_dim % self.num_bytes != 0:
            raise ValueError('vec dim should be divided by x')
        self.x = int(self.vec_dim / self.num_bytes)
        self.mean = np.mean(vecs, axis=0)
        self.var = np.var(vecs, axis=0)
        self.matrixs = [self.ran_gen() for _ in range(self.num_bytes)]
        self.proj = np.array([2**i for i in range(self.num_clusters)]).astype(np.int32)

    def ran_gen(self, method='uniform'):
        if method == 'uniform':
            return np.random.uniform(-1, 1, size=(self.x, self.num_clusters)
                                     ).astype(np.float32)

    @train_required
    @batching(batch_size=2048)
    def encode(self, vecs: np.ndarray, *args, **kwargs) -> np.ndarray:
        vecs = (vecs - self.mean) / self.var
        vecs = np.reshape(vecs, [vecs.shape[0], self.num_bytes, self.x])
        outcome = []
        for i in range(self.num_bytes):
            out = np.matmul(vecs[:, i, :], self.matrixs[i])
            out = np.greater(out, 0)
            outcome.append(np.sum(out * self.proj, axis=1, keepdims=1))
        outcome = np.concatenate(outcome, axis=1).astype(np.uint8)
        return outcome

    def _copy_from(self, x: 'HashEncoder') -> None:
        self.num_bytes = x.num_bytes
        self.num_clusters = x.cluster_per_byte
        self.x = x.x
        self.vec_dim = x.vec_dim
        self.matrixs = x.matrixs
        self.mean = x.mean
        self.var = x.var
        self.is_trained = x.is_trained
