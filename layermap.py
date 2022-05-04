import os
from . import units
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import copy

class LayerMapEditor():
    def __init__(self, layermap_file, defLen="m", defCond="S/m"):
        self.um = units.UnitManager()
        self.cmds = {
            "assume":{
                "opts":["phyName","unitName"],
                "minOpts":2},
            "layer":{
                "opts":["layerName","height","dielectric","conductivity","tandel"],
                "minOpts":3},
            "conductor":{
                "opts":["condName","height","conductivity","offset","bias"],
                "minOpts":3},
            "via":{
                "opts":["viaName","bottomCondName","topCondName","conductivity"],
                "minOpts":4}
        }
        self.opts = {
            "phyName":{"key":"-pn","dim":"string"},
            "unitName":{"key":"-un","dim":"string"},
            "layerName":{"key":"-ln","dim":"string"},
            "height":{"key":"-h","dim":"length"},
            "dielectric":{"key":"-d","dim":"dimless"},
            "tandel":{"key":"-t","dim":"dimless"},
            "condName":{"key":"-cn","dim":"string"},
            "conductivity":{"key":"-c","dim":"conductivity"},
            "offset":{"key":"-o","dim":"length"},
            "bias":{"key":"-b","dim":"length"},
            "viaName":{"key":"-vn","dim":"string"},
            "bottomCondName":{"key":"-bcn","dim":"string"},
            "topCondName":{"key":"-tcn","dim":"string"},
        }
        self.dims = {
            "string":{
                "defUnit":"__",
                "dtype":str},
            "dimless":{
                "defUnit":"-",
                "dtype":float},
            "length":{
                "defUnit":defLen,
                "dtype":float},
            "conductivity":{
                "defUnit":defCond,
                "dtype":float}
        }
        self.initlayerData()
        self.importFile(layermap_file)

    def initlayerData(self):
        self.layerData = {"stack":{}, "materials":{}, "num":{"layer":0, "conductor":0, "via":0}, "unit":{"length":None, "conductivity":None}}

    def isNum(self, str):
        try:
            float(str.replace(',',''))
        except ValueError:
            return False
        else:
            return True

    def strToFloat(self, val):
        if self.isNum(val):
            return float(val)
        elif val in ["nan","inf","-inf"]:
            return float(val)
        else:
            return val

    def transArgs(self, cmd, args):
        try:
            allOpts = self.cmds[cmd]["opts"]
            allKeys = [self.opts[opt]["key"] for opt in allOpts]
            allDefUnits = [self.dims[self.opts[opt]["dim"]]["defUnit"] for opt in allOpts]
            sprArgs = []
            retArgs = {opt:{"val":None,"unit":None} for opt in allOpts}

            args = list(map(self.strToFloat, args))
            args.append("EOA")
            crIdx, tmpArg = (0,None)
            for i,arg in enumerate(args):
                if tmpArg in allKeys:
                    pass
                elif type(tmpArg) is float and self.um.isValid(arg):
                    pass
                else:
                    if crIdx<i:
                        sprArgs.append(args[crIdx:i])
                        crIdx = i
                tmpArg = arg

            for i,args in enumerate(sprArgs):
                opt,unit,val = (None,None,None)
                for j,arg in enumerate(args):
                    if arg in allKeys:
                        opt = allOpts[allKeys.index(arg)]
                    elif self.um.isValid(arg):
                        if val is None:
                            val = arg
                        elif type(val) is float:
                            unit = arg
                        else:
                            raise optError("inValidUnit", i, arg)
                    else:
                        val = arg

                idx = None
                if opt is None:
                    retVal = [v["val"] for v in retArgs.values()]
                    if None not in retVal:
                        raise optError("overArgs", len(self.cmds[cmd]["opts"]))
                    idx = retVal.index(None)
                    opt = allOpts[idx]
                else:
                    idx = allOpts.index(opt)
                unit = unit if unit else allDefUnits[idx]
                retArgs[opt]["val"] = val
                retArgs[opt]["unit"] = unit

            if None in list(retArgs.values())[0:self.cmds[cmd]["minOpts"]]:
                raise optError("lessArgs", self.cmds[cmd]["minOpts"])
            return copy.deepcopy(retArgs)

        except optError as e:
            raise optError(*e.args)

    def convResistivity(self, t, val, unit1=None, unit2=None):
        t = self.um.convUnit(val=t,unit1=self.dims["length"]["defUnit"])
        unit1 = unit1 if unit1 else self.dims["conductivity"]["defUnit"]
        unit2 = unit2 if unit2 else self.dims["conductivity"]["defUnit"]
        dimC1 = self.um.getDimName(unit1)
        dimC2 = self.um.getDimName(unit2)
        val = self.um.convUnit(val=val,unit1=unit1)
        val = self.um.transResistivity(t, val, dimC1, dimC2)
        val = self.um.convUnit(val=val,unit2=unit2)
        return val

    def convDefUnit(self, opt, val, unit):
        unit2 = self.dims[self.opts[opt]["dim"]]["defUnit"]
        if type(val) is float:
            return self.um.convUnit(val=val,unit1=unit,unit2=unit2)
        else:
            return val

    def updateUnit(self, dim, unit):
        try:
            if dim not in self.dims.keys():
                raise optError("unDefDimName", dim)
            elif not self.um.isValid(unit):
                raise optError("inValidUnitName", unit)
            self.dims[dim]["defUnit"] = unit

        except optError as e:
            raise optError(*e.args)

    def importFile(self, fileName, matPrefix='T65_'):
        self.initlayerData()

        crHg = [0,0]
        cmds = list(self.cmds.keys())
        with open(fileName, mode='r') as f:
            try:
                for i,row in enumerate(f):
                    str_arr = row.split()
                    if str_arr==[]:
                        continue

                    cmd = str_arr[0]
                    args = str_arr[1:]
                    if cmd=="#":
                        continue
                    elif cmd not in cmds:
                        raise cmdError("unDefCmd",i,cmd)

                    try:
                        dictArgs = self.transArgs(cmd, args)
                    except optError as e:
                        args = list(e.args)
                        args.insert(1, i)
                        raise optError(*args)

                    if cmd==cmds[0]:
                        try:
                            self.updateUnit(dictArgs["phyName"]["val"], dictArgs["unitName"]["val"])
                        except optError as e:
                            args = list(e.args)
                            args.insert(1, i)
                            raise optError(*args)

                    elif cmd==cmds[1]:
                        layerName = dictArgs["layerName"]["val"]
                        h = self.convDefUnit("height",dictArgs["height"]["val"],dictArgs["height"]["unit"])
                        dc = self.convDefUnit("dielectric",dictArgs["dielectric"]["val"],dictArgs["dielectric"]["unit"])
                        cond = self.convResistivity(h,dictArgs["conductivity"]["val"],dictArgs["conductivity"]["unit"]) if dictArgs["conductivity"]["val"] else np.nan
                        tandel = self.convDefUnit("tandel",dictArgs["tandel"]["val"],dictArgs["tandel"]["unit"]) if dictArgs["tandel"]["val"] else np.nan

                        matName = matPrefix+layerName
                        range = [crHg[1], crHg[1]+h]

                        self.layerData["stack"][layerName] = {
                            "type":"dielectric",
                            "material":matName,
                            "height":h,
                            "range":range}
                        self.layerData["materials"][matName] = {
                            "type":"dielectric",
                            "constant":dc,
                            "conductivity":cond,
                            "height":h,
                            "tandel":tandel}
                        self.layerData["num"]["layer"] += 1
                        crHg = range.copy()

                    elif cmd==cmds[2]:
                        condName = dictArgs["condName"]["val"]
                        h = self.convDefUnit("height",dictArgs["height"]["val"],dictArgs["height"]["unit"])
                        cond = self.convResistivity(h,dictArgs["conductivity"]["val"],dictArgs["conductivity"]["unit"])
                        offset = self.convDefUnit("offset",dictArgs["offset"]["val"],dictArgs["offset"]["unit"]) if dictArgs["offset"]["val"] else 0.0
                        bias = self.convDefUnit("bias",dictArgs["bias"]["val"],dictArgs["bias"]["unit"]) if dictArgs["bias"]["val"] else 0.0

                        matName = matPrefix+condName
                        range = [crHg[0]+offset-bias/2, crHg[0]+offset+h+bias/2]

                        self.layerData["stack"][condName] = {
                            "type":"conductor",
                            "material":matName,
                            "height":h+bias,
                            "range":range,
                            "offset":offset-bias/2,
                            "origin":crHg[0]}
                        self.layerData["materials"][matName] = {
                            "type":"conductor",
                            "conductivity":cond,
                            "height":h}
                        self.layerData["num"]["conductor"] += 1

                    elif cmd==cmds[3]:
                        viaName = dictArgs["viaName"]["val"]
                        btmCondName = dictArgs["bottomCondName"]["val"]
                        topCondName = dictArgs["topCondName"]["val"]

                        if btmCondName not in self.layerData["stack"].keys():
                            raise optError("unDefCondName",i,btmCondName)
                        if topCondName not in self.layerData["stack"].keys():
                            raise optError("unDefCondName",i,topCondName)
                        range1 = self.layerData["stack"][btmCondName]["range"]
                        range2 = self.layerData["stack"][topCondName]["range"]
                        if range1[1]<=range2[0]:
                            range = [range1[1], range2[0]]
                            offset = self.layerData["stack"][btmCondName]["offset"]
                            origin = self.layerData["stack"][btmCondName]["origin"]
                        else:
                            range = [range2[1], range1[0]]
                            offset = self.layerData["stack"][topCondName]["offset"]
                            origin = self.layerData["stack"][topCondName]["origin"]

                        matName = matPrefix+viaName
                        h = range[1]-range[0]
                        cond = self.convResistivity(h,dictArgs["conductivity"]["val"],dictArgs["conductivity"]["unit"])

                        self.layerData["stack"][viaName] = {
                            "type":"via",
                            "material":matName,
                            "height":h,
                            "range":range,
                            "offset":offset,
                            "origin":origin}
                        self.layerData["materials"][matName] = {
                            "type":"conductor",
                            "conductivity":cond,
                            "height":h}
                        self.layerData["num"]["via"] += 1

            except cmdError as e:
                if e.args[0]=="unDefCmd":
                    msg = f"Undefined command \"{e.args[2]}\" at {e.args[1]} line."
                print("Command Error: "+msg)

            except optError as e:
                if e.args[0]=="lessArgs":
                    msg = f"At least {e.args[2]} arguments are required at {e.args[1]} line."
                elif e.args[0]=="overArgs":
                    msg = f"Too many arguments at {e.args[1]} line, maximum is {e.args[2]}."
                elif e.args[0]=="inValidUnit":
                    msg = f"Invalid unit \"{e.args[3]}\" at {e.args[1]} line, {e.args[2]} argument."
                elif e.args[0]=="unDefCondName":
                    msg = f"Undefined conductor name \"{e.args[2]}\" at {e.args[1]} line."
                elif e.args[0]=="unDefDimName":
                    msg = f"Undefined dimension name \"{e.args[2]}\" at {e.args[1]} line."
                elif e.args[0]=="inValidUnitName":
                    msg = f"Invalid unit name \"{e.args[2]}\" at {e.args[1]} line."
                print("Option Error: "+msg)

    def mergeLayers(self, layerName1, layerName2, newLayerName, layerData=None, matPrefix="T65_", overWrite=True):
        inFlag = False
        newLayerData = copy.deepcopy(layerData if layerData else self.layerData)
        newRange = [newLayerData["stack"][layerName1]["range"][0],newLayerData["stack"][layerName2]["range"][1]]
        dpeSum = 0
        for lName,lData in copy.deepcopy(newLayerData["stack"]).items():
            if lData["type"]=="dielectric":
                if newRange[0]<=lData["range"][0] and lData["range"][1]<=newRange[1]:
                    eps = newLayerData["materials"][lData["material"]]["constant"]
                    dpeSum += lData["height"]/eps
                    if lName==layerName2:
                        ht = newRange[1]-newRange[0]
                        epsNew = ht/dpeSum
                        newMatName = matPrefix+newLayerName
                        newLayerData["stack"][lName]["height"] = ht
                        newLayerData["stack"][lName]["range"] = newRange
                        newLayerData["stack"][lName]["material"] = newMatName
                        newLayerData["materials"][newMatName] = {
                            "type":"dielectric",
                            "constant":epsNew,
                            "conductivity":np.nan,
                            "height":ht,
                            "tandel":np.nan}
                        break
                    else:
                        del newLayerData["stack"][lName]
        newLayerData["stack"] = {newLayerName if lName==layerName2 else lName:lData for lName,lData in newLayerData["stack"].items()}
        newLayerData = self.delUnusedMat(layerData=newLayerData,overWrite=False)
        if overWrite:
            self.layerData = newLayerData
        return newLayerData

    def delUnusedMat(self, layerData=None, overWrite=True):
        newLayerData = copy.deepcopy(layerData if layerData else self.layerData)
        usedMat = [lData["material"] for lData in newLayerData["stack"].values()]
        for mName,mData in copy.deepcopy(newLayerData["materials"]).items():
            if mName not in usedMat:
                del newLayerData["materials"][mName]
        if overWrite:
            self.layerData = newLayerData
        return newLayerData

    def changeMatCond(self, unit):
        for mData in self.layerData["materials"].values():
            h = mData["height"]
            mData["conductivity"] = self.convResistivity(t=h,val=mData["conductivity"],unit2=unit)
        self.updateUnit("conductivity",unit)

    def plotStack(self, scaled=True, layerColor=("green",0.2), condColor=("orange",1), viaColor=("yellow",0.5)):
        maxHg = np.max([lData["range"] for lData in self.layerData["stack"].values()])
        w0 = maxHg/5
        h0 = maxHg/self.layerData["num"]["layer"]
        figSize = 50
        maxFontSize = 20

        pltLayerStack = copy.deepcopy(self.layerData["stack"])
        pltCrHg = 0
        for lName,lData in self.layerData["stack"].items():
            if lData["type"]=="dielectric":
                ly0,ly1 = lData["range"]
                h = h0 if scaled else ly1-ly0
                lRatio = h/(ly1-ly0)
                pltLayerStack[lName]["range"] = (pltCrHg,pltCrHg+h)

                for cName,cData in self.layerData["stack"].items():
                    if cData["type"] in ["conductor","via"]:
                        cy0,cy1 = cData["range"]
                        if ly1<cy0 or cy1<ly0:
                            continue
                        if cy0>=ly0:
                            pltLayerStack[cName]["range"][0] = pltLayerStack[lName]["range"][0]+(cy0-ly0)*lRatio
                        if cy1<=ly1:
                            pltLayerStack[cName]["range"][1] = pltLayerStack[lName]["range"][1]-(ly1-cy1)*lRatio
                pltCrHg += h

        for lName,lData in pltLayerStack.items():
            if lData["type"]=="dielectric":
                lData["pos"] = (0,lData["range"][0])
                lData["width"] = w0
                lData["color"] = layerColor
            elif lData["type"]=="conductor":
                lData["pos"] = (w0,lData["range"][0])
                lData["width"] = w0
                lData["color"] = condColor
            elif lData["type"]=="via":
                numDpl = 0
                for vName,vData in pltLayerStack.items():
                    if vData["type"]=="via":
                        if vName==lName:
                            break
                        elif lData["range"][1]<vData["range"][0] or vData["range"][1]<lData["range"][0]:
                            pass
                        else:
                            numDpl += 1
                lData["pos"] = (2*w0+w0*numDpl,lData["range"][0])
                lData["width"] = w0
                lData["color"] = viaColor

        fig = plt.figure(figsize=(figSize,figSize))
        ax = fig.add_subplot(111)
        for lName,lData in pltLayerStack.items():
            fontSize = 5000*(lData["range"][1]-lData["range"][0])/maxHg
            fontSize = fontSize if fontSize<maxFontSize else maxFontSize
            if lData["type"]=="dielectric":
                matVal = f'eps{self.layerData["materials"][lData["material"]]["constant"]:.2f}'
                plt.text(lData["pos"][0]-lData["width"]/2,lData["range"][1],f'{self.layerData["stack"][lName]["range"][1]:.3f}{self.dims["length"]["defUnit"]}',size=fontSize)
                plt.hlines(lData["range"][0],lData["pos"][0]-lData["width"]/2,lData["pos"][0],linewidths=0.5,color="black",alpha=1.0)
                plt.hlines(lData["range"][1],lData["pos"][0]-lData["width"]/2,lData["pos"][0],linewidths=0.5,color="black",alpha=1.0)
            elif lData["type"]=="conductor":
                matVal = f'{self.layerData["materials"][lData["material"]]["conductivity"]:.3f}{self.dims["conductivity"]["defUnit"]}'
            elif lData["type"]=="via":
                matVal = f'{self.layerData["materials"][lData["material"]]["conductivity"]:.3f}{self.dims["conductivity"]["defUnit"]}'

            r = patches.Rectangle(
                xy=lData["pos"],
                width=lData["width"],
                height=lData["range"][1]-lData["range"][0],
                color=lData["color"][0],
                alpha=lData["color"][1])
            ax.add_patch(r)

            plt.text(
                x=lData["pos"][0]+lData["width"]/2,
                y=lData["pos"][1]+(lData["range"][1]-lData["range"][0])/2,
                s=f'{lName}:{matVal},h{self.layerData["stack"][lName]["height"]:.3f}{self.dims["length"]["defUnit"]}',
                size=fontSize,
                va="center", ha="center")
        plt.axis('scaled')
        ax.set_aspect('equal')
        ax.axes.xaxis.set_visible(False)
        ax.axes.yaxis.set_visible(False)
        plt.show()

class cmdError(Exception):
    pass
class optError(Exception):
    pass

if __name__=='__main__':
    lme = LayerMapEditor("./emx_layermap/tsmc65n.txt")
    lme.plotStack()
    lme.mergeLayers(layerName1="FOX",layerName2="ILD0b",newLayerName="IMD1A")
    lme.mergeLayers(layerName1="IMD1a",layerName2="IMD1b",newLayerName="IMD1B")

    lme.mergeLayers(layerName1="IMD1c",layerName2="IMD2a",newLayerName="IMD2A")
    lme.mergeLayers(layerName1="IMD2b",layerName2="IMD2b",newLayerName="IMD2B")

    lme.mergeLayers(layerName1="IMD2c",layerName2="IMD3a",newLayerName="IMD3A")
    lme.mergeLayers(layerName1="IMD3b",layerName2="IMD3b",newLayerName="IMD3B")

    lme.mergeLayers(layerName1="IMD3c",layerName2="IMD4a",newLayerName="IMD4A")
    lme.mergeLayers(layerName1="IMD4b",layerName2="IMD4b",newLayerName="IMD4B")

    lme.mergeLayers(layerName1="IMD4c",layerName2="IMD5a",newLayerName="IMD5A")
    lme.mergeLayers(layerName1="IMD5b",layerName2="IMD5b",newLayerName="IMD5B")

    lme.mergeLayers(layerName1="IMD5c",layerName2="IMD6a",newLayerName="IMD6A")
    lme.mergeLayers(layerName1="IMD6b",layerName2="IMD6b",newLayerName="IMD6B")

    lme.mergeLayers(layerName1="IMD6c",layerName2="IMD7a",newLayerName="IMD7A")
    lme.mergeLayers(layerName1="IMD7b",layerName2="IMD7b",newLayerName="IMD7B")
    lme.mergeLayers(layerName1="IMD7c",layerName2="IMD7c",newLayerName="IMD7C")

    lme.mergeLayers(layerName1="IMD8a",layerName2="IMD8a",newLayerName="IMD8A")
    lme.mergeLayers(layerName1="IMD8b",layerName2="IMD8c",newLayerName="IMD8B")

    lme.mergeLayers(layerName1="IMD8d",layerName2="IMD9a",newLayerName="IMD9A")
    lme.mergeLayers(layerName1="IMD9b",layerName2="IMD9c",newLayerName="IMD9B")

    lme.mergeLayers(layerName1="PASS1",layerName2="PASS4",newLayerName="PASS1A")
    lme.mergeLayers(layerName1="PASS5a",layerName2="PASS5a",newLayerName="PASS1B")
    lme.mergeLayers(layerName1="PASS5b",layerName2="PASS6",newLayerName="PASS1C")

    lme.changeMatCond("S/m")
    lme.plotStack()
