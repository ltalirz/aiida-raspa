#!/usr/bin/env python2
# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c), The AiiDA team. All rights reserved.                        #
# This file is part of the AiiDA code.                                       #
#                                                                            #
# The code is hosted on GitHub at https://github.com/yakutovicha/aiida-raspa #
# For further information on the license, see the LICENSE.txt file           #
# For further information please visit http://www.aiida.net                  #
##############################################################################
from __future__ import print_function

from __future__ import absolute_import
import sys
import os

from aiida.common.example_helpers import test_and_get_code
from aiida.orm.utils import DataFactory

# data objects
CifData = DataFactory('cif')
ParameterData = DataFactory('parameter')
SinglefileData = DataFactory('singlefile')

# ==============================================================================
if len(sys.argv) != 2:
    print("Usage: test_raspa.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
code = test_and_get_code(codename, expected_code_type='raspa')

print("Testing RASPA...")

# calc object
calc = code.new_calc()

# parameters
parameters = ParameterData(
    dict={
        "GeneralSettings": {
            "SimulationType": "MonteCarlo",
            "NumberOfCycles": 2000,
            "NumberOfInitializationCycles": 2000,
            "PrintEvery": 1000,
            "Forcefield": "GenericMOFs",
            "EwaldPrecision": 1e-6,
            "CutOff": 12.0,
            "Framework": 0,
            "UnitCells": "1 1 1",
            "HeliumVoidFraction": 0.149,
            "ExternalTemperature": 300.0,
            "ExternalPressure": 5e5,
        },
        "Component": [{
            "MoleculeName": "methane",
            "MoleculeDefinition": "TraPPE",
            "TranslationProbability": 0.5,
            "ReinsertionProbability": 0.5,
            "SwapProbability": 1.0,
            "CreateNumberOfMolecules": 0,
        }],
    })
calc.use_parameters(parameters)

# structure
pwd = os.path.dirname(os.path.realpath(__file__))
framework = CifData(file=pwd + '/test_raspa_attach_file/TCC1RS.cif')
calc.use_structure(framework)

# resources
calc.set_max_wallclock_seconds(30 * 60)  # 30 min
calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})
calc.set_withmpi(False)
#calc.set_queue_name("serial")

# store and submit
calc.store_all()
calc.submit()

#calc.submit_test()
print("submitted calculation: PK=%s" % calc.pk)
# EOF
