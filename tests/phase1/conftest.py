import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def context():
    c=np.linspace(10,20,121)
    return pd.DataFrame({'date':np.arange(121),'close':c,'high':c+1,'low':c-1,
                         'amount':np.linspace(100,200,121),'synthetic':False,'state':'BAR'})
