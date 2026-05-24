from chimera import runCommand, openModels
import WriteDMS
import _surface

# load structure
runCommand("open /localscratch/kbui/NexusMol/examples/artifacts/dock6_mpro/6W63_prepared_noH.mol2")

# generate molecular surface
runCommand("surface")

# get generated surface model
surfs = openModels.list(modelTypes=[_surface.SurfaceModel])

surf = surfs[0]

# write DMS
WriteDMS.writeDMS(surf, "6W63_rec.dms")

runCommand("stop")