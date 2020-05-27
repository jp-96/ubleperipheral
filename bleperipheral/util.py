'''
bleperipheral package
Copyright (c) 2020 jp-96
'''

def _f():
    pass

async def _g():
    pass

class _B():
    def _b(self):
        pass

_type_function = type(_f)
_type_generator = type(_g)
_type_bound_method = type(_B()._b)

def isFunction(obj):
    return type(obj) == _type_function

def isGenerator(obj):
    return type(obj) == _type_generator

def isBoundMethod(obj):
    return type(obj) == _type_bound_method
