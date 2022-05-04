import re
import numpy as np

# Define Units #################################################################
available_units = {
    'physical_quantity':{
        'string'        :'__',
        'dimless'       :'-',
        'time'          :'sec',
        'length'        :'m',
        'frequency'     :'Hz',
        'voltage'       :'V',
        'current'       :'A',
        'power'         :'W',
        'power_dBm'     :'dBm',
        'decibel'       :'dB',
        'percentage'    :'per',
        'conductance'   :'S',
        'resistance'    :'ohm',
        'conductivity'  :'S/m',
        'resistivity'   :'ohm*m',
        'sheet_resistance':'ohm/sq'
    },
    'special_quantity':{
        'area'          :['m2', 'm*m'],
        'volume'        :['m3', 'm*m*m']
    },
    'unit_prefix':{
        'T' :1.0e12,
        'G' :1.0e9,
        'M' :1.0e6,
        'k' :1.0e3,
        ''  :1.0,
        'm' :1.0e-3,
        'u' :1.0e-6,
        'n' :1.0e-9,
        'f' :1.0e-12
    }
}
class UnitManager():
    def __init__(self):
        self.units = {}
        self.genUnits()

    def genUnits(self):
        self.units = {}
        for dim,pq in available_units['physical_quantity'].items():
            self.units[dim] = {}
            pq_arr = re.split(r'[/*]', pq)
            pq_num = re.findall(r'\*(\w*)', pq)
            pq_num.append(pq_arr[0])
            pq_denom = re.findall(r'\/(\w*)', pq)
            for i,sub_pq in enumerate(pq_arr):
                for pf, dg in available_units['unit_prefix'].items():
                    for j,tmp in enumerate(pq_arr):
                        join_char = '*' if tmp in pq_num else '/'
                        tmp = tmp if j!=i else f'{pf}{tmp}'
                        vname = tmp if j==0 else vname+join_char+tmp
                    dg = dg if sub_pq in pq_num else 1/dg
                    self.units[dim][vname] = dg

    def getUnits(self, dim):
        return self.units[dim].copy()

    def getUnitNames(self, dim):
        return list(self.units[dim].keys())

    def isValid(self, uname):
        return uname in self.getAllUnits().keys()

    def getUnitVal(self, uname):
        if self.isValid(uname):
            return self.getAllUnits()[uname]
        else:
            return None

    def getAllUnits(self):
        all_units = {}
        for units in self.units.values():
            all_units.update(units)
        return all_units.copy()

    def getDimName(self, uname):
        if self.isValid(uname):
            for dim,units in self.units.items():
                if uname in list(units.keys()):
                    return dim
        else:
            return None

    def getRelatives(self, uname):
        dim = self.getDimName(uname)
        if dim:
            return self.getUnits(dim)
        else:
            return None

    def getBaseUnit(self, uname):
        dim = self.getDimName(uname)
        if dim:
            return available_units['physical_quantity'][dim]
        else:
            return None

    def convUnit(self, val, unit1=None, unit2=None):
        dig1 = self.getUnitVal(unit1) if unit1 else 1
        dig2 = self.getUnitVal(unit2) if unit2 else 1
        return val*dig1/dig2

    def calcResistivity(self, t, pr=np.nan, pc=np.nan, rs=np.nan):
        retArr = np.full((3,3), np.nan)
        retArr[0][0] = pr
        retArr[0][1] = 1/pr
        retArr[0][2] = pr/t
        retArr[1][0] = 1/pc
        retArr[1][1] = pc
        retArr[1][2] = 1/(t*pc)
        retArr[2][0] = t*rs
        retArr[2][1] = 1/(t*rs)
        retArr[2][2] = rs
        return retArr

    def transResistivity(self, t, val, dim1, dim2):
        row = 0
        if dim1=="resistivity":
            row = 0
        elif dim1=="conductivity":
            row = 1
        elif dim1=="sheet_resistance":
            row = 2

        col = 0
        if dim2=="resistivity":
            col = 0
        elif dim2=="conductivity":
            col = 1
        elif dim2=="sheet_resistance":
            col = 2

        arr = self.calcResistivity(t,val,val,val)
        return arr[row][col]



if __name__=='__main__':
    um = UnitManager()
    print(um.getUnitNames("conductivity"))
    print(um.isValid("AAA"))
    print(um.isValid("nm"))
    print(um.getUnitVal("AAA"))
    print(um.getUnitVal("nm"))
    print(um.getAllUnits())
    print(um.getRelatives("nm"))
