# -*- coding: utf-8 -*-
"""Extract IL2CPP string literals from global-metadata.dat (v29) and hunt for keys."""
import os, re, struct, sys, math, collections

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
mp = os.path.join(root, 'il2cpp', 'Metadata', 'global-metadata.dat')
b = open(mp, 'rb').read()

hdr = struct.unpack_from('<Ii', b, 0)
print('sanity %08x version %d' % (hdr[0] & 0xffffffff, hdr[1]))
fields = struct.unpack_from('<' + 'i' * 62, b, 8)
names = ['stringLiteralOffset','stringLiteralCount','stringLiteralDataOffset','stringLiteralDataCount',
         'stringOffset','stringCount','stringDataOffset','stringDataCount',
         'eventsOffset','eventsCount','propertiesOffset','propertiesCount',
         'methodsOffset','methodsCount','parameterDefaultValuesOffset','parameterDefaultValuesCount',
         'fieldDefaultValuesOffset','fieldDefaultValuesCount','fieldAndParameterDefaultValueDataOffset','fieldAndParameterDefaultValueDataCount',
         'fieldMarshaledSizesOffset','fieldMarshaledSizesCount','parametersOffset','parametersCount',
         'fieldsOffset','fieldsCount','genericParametersOffset','genericParametersCount',
         'genericParameterConstraintsOffset','genericParameterConstraintsCount','genericContainersOffset','genericContainersCount',
         'nestedTypesOffset','nestedTypesCount','interfacesOffset','interfacesCount',
         'vtableMethodsOffset','vtableMethodsCount','interfaceOffsetsOffset','interfaceOffsetsCount',
         'typeDefinitionsOffset','typeDefinitionsCount','imagesOffset','imagesCount',
         'assembliesOffset','assembliesCount','fieldRefsOffset','fieldRefsCount',
         'referencedAssembliesOffset','referencedAssembliesCount','attributeDataOffset','attributeDataCount',
         'attributeDataRangeOffset','attributeDataRangeCount','unresolvedVirtualCallParameterTypesOffset','unresolvedVirtualCallParameterTypesCount',
         'unresolvedVirtualCallParameterRangesOffset','unresolvedVirtualCallParameterRangesCount','windowsRuntimeTypeNamesOffset','windowsRuntimeTypeNamesSize',
         'exportedTypeDefinitionsOffset','exportedTypeDefinitionsCount','windowsRuntimeStringsOffset','windowsRuntimeStringsSize']
for n, v in zip(names, fields):
    print('  %-46s %d' % (n, v))
