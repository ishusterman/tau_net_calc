# -*- coding: utf-8 -*-
import os
import site
site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/cls'))

def classFactory(iface):    
    from .tau_net_calc import TAUNetCalc
    return TAUNetCalc(iface)
