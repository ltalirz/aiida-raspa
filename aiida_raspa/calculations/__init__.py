# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA team. All rights reserved.                         #
# This file is part of the AiiDA code.                                        #
#                                                                             #
# The code is hosted on GitHub at https://github.com/yakutovicha/aiida-raspa  #
# For further information on the license, see the LICENSE.txt file            #
# For further information please visit http://www.aiida.net                   #
###############################################################################

from aiida.orm.calculation.job import JobCalculation
from aiida.common.utils import classproperty
from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.singlefile import SinglefileData
from aiida.orm.data.remote import RemoteData
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.exceptions import InputValidationError


class RaspaCalculation(JobCalculation):
    """
    This is a RaspaCalculation, subclass of JobCalculation,
    to prepare input for an RaspaCalculation.
    For information on RASPA, refer to: https://github.com/numat/RASPA2
    """

    # --------------------------------------------------------------------------
    def _init_internal_params(self):
        """
        Set parameters of instance
        """
        super(RaspaCalculation, self)._init_internal_params()
        self._INPUT_FILE_NAME = 'simulation.input'
        self._OUTPUT_FILE_NAME = 'Output/System*/*dat'
        self._DEFAULT_INPUT_FILE = self._INPUT_FILE_NAME
        self._DEFAULT_OUTPUT_FILE = self._OUTPUT_FILE_NAME
        self._PROJECT_NAME = 'aiida'
        self._COORDS_FILE_NAME = 'aiida.coords.xyz'
        self._default_parser = 'raspa'

    # --------------------------------------------------------------------------
    @classproperty
    def _use_methods(cls):
        """
        Extend the parent _use_methods with further keys.
        This will be manually added to the _use_methods in each subclass
        """
        retdict = JobCalculation._use_methods
        retdict.update({
            "structure": {
               'valid_types': StructureData,
               'additional_parameter': None,
               'linkname': 'structure',
               'docstring': "Choose the input structure to use",
               },
            "settings": {
               'valid_types': ParameterData,
               'additional_parameter': None,
               'linkname': 'settings',
               'docstring': "Use an additional node for special settings",
               },
            "parameters": {
               'valid_types': ParameterData,
               'additional_parameter': None,
               'linkname': 'parameters',
               'docstring': "Use a node that specifies the "
                            "input parameters for the namelists",
               },
            "file": {
               'valid_types': SinglefileData,
               'additional_parameter': "linkname",
               'linkname': cls._get_linkname_file,
               'docstring': "Use files to provide additional parameters",
               },
            })
        return retdict

    # --------------------------------------------------------------------------
    @classmethod
    def _get_linkname_file(cls, linkname):
        return(linkname)

    # --------------------------------------------------------------------------
    def _prepare_for_submission(self, tempfolder, inputdict):
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """

        in_nodes = self._verify_inlinks(inputdict)
        params, structure, code, settings, local_copy_list = in_nodes

        # write cp2k input file
        inp = RaspaInput(params)
        inp_fn = tempfolder.get_abs_path(self._INPUT_FILE_NAME)
        with open(inp_fn, "w") as f:
            f.write(inp.render())

        # create code info
        codeinfo = CodeInfo()
        cmdline = settings.pop('cmdline', [])
        cmdline += [self._INPUT_FILE_NAME]
        codeinfo.cmdline_params = cmdline
        codeinfo.code_uuid = code.uuid

        # create calc info
        calcinfo = CalcInfo()
        calcinfo.stdin_name = self._INPUT_FILE_NAME
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._INPUT_FILE_NAME
#        calcinfo.stdout_name = self._OUTPUT_FILE_NAME
        calcinfo.codes_info = [codeinfo]

        # file lists
        calcinfo.remote_symlink_list = []
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = []
        calcinfo.retrieve_list = [[self._OUTPUT_FILE_NAME,'.',0]]
        calcinfo.retrieve_list += settings.pop('additional_retrieve_list', [])


        # check for left over settings
        if settings:
            msg = "The following keys have been found "
            msg += "in the settings input node {}, ".format(self.pk)
            msg += "but were not understood: " + ",".join(settings.keys())
            raise InputValidationError(msg)

        return calcinfo

    # --------------------------------------------------------------------------
    def _verify_inlinks(self, inputdict):
        # parameters
        params_node = inputdict.pop('parameters', None)
        if params_node is None:
            raise InputValidationError("No parameters specified")
        if not isinstance(params_node, ParameterData):
            raise InputValidationError("parameters type not ParameterData")
        params = params_node.get_dict()

        # structure
        structure = inputdict.pop('structure', None)
        if structure is not None:
            if not isinstance(structure, StructureData):
                raise InputValidationError("structure type not StructureData")

        # code
        code = inputdict.pop(self.get_linkname('code'), None)
        if code is None:
            raise InputValidationError("No code specified")

        # settings
        # ... if not provided fall back to empty dict
        settings_node = inputdict.pop('settings', ParameterData())
        if not isinstance(settings_node, ParameterData):
            raise InputValidationError("settings type not ParameterData")
        settings = settings_node.get_dict()


        # handle additional parameter files
        local_copy_list = []
        for k, v in inputdict.items():
            if isinstance(v, SinglefileData):
                inputdict.pop(k)
                local_copy_list.append((v.get_file_abs_path(), v.filename))

        if inputdict:
            msg = "unrecognized input nodes: " + str(inputdict.keys())
            raise InputValidationError(msg)

        return(params, structure, code, settings, local_copy_list)


# ==============================================================================
class RaspaInput(object):
    def __init__(self, params):
        self.params = params
    # --------------------------------------------------------------------------
    def render(self):
        output = ["!!! Generated by AiiDA !!!"]
        val=self.params.pop("GeneralSettings")
        self._render_section(output, val)
        val=self.params.pop("Component")
        self._render_section(output, {"Component": val})
        return "\n".join(output)

    # --------------------------------------------------------------------------
    def _render_section(self, output, params, indent=0):
        """
        It takes a dictionary and recurses through.

        For key-value pair it checks whether the value is a dictionary
        and prepends the key with &
        It passes the valued to the same function, increasing the indentation
        If the value is a list, I assume that this is something the user
        wants to store repetitively
        """
#        output.append("enter")
#        output.append("This what comes:" + str(params))
        for key, val in sorted(params.items()):
            if isinstance(val, dict):
                output.append('%s %s %s %s' % (key, val.pop('_', ''),
                'MoleculeName', val.pop('MoleculeName', '')))
                self._render_section(output, val, indent + 3) 
            elif isinstance(val, list):
                for listitem in val:
                    self._render_section(output,  {key: listitem}, indent)
            elif isinstance(val, bool):
                val_str = '.true.' if val else '.false.'
                output.append('%s%s  %s' % (' '*indent, key, val_str))
            else:
                output.append('%s%s  %s' % (' '*indent, key, val))
#        output.append('exit')

# EOF
