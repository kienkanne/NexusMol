from chimera import runCommand, openModels
import WriteDMS
import _surface

# load structure
runCommand("open $prepped_receptor_noH_mol2")

# generate molecular surface
runCommand("surface")

# get generated surface model
surfs = openModels.list(modelTypes=[_surface.SurfaceModel])

surf = surfs[0]

# write DMS
WriteDMS.writeDMS(surf, "${name}_rec.dms")

runCommand("stop")