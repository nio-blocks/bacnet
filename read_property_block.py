# Bacpypes sets _root_logger to DEBUG, this resets it after bacpypes has
# finished importing.
# This may cause other nio threads to momentarily log at DEBUG level.
import logging
_root_logger = logging.getLogger()
_root_logger_level = _root_logger.level
from bacpypes.apdu import ReadPropertyRequest, ReadPropertyACK
from bacpypes.app import BIPSimpleApplication
from bacpypes.core import run, stop
from bacpypes.iocb import IOCB
from bacpypes.local.device import LocalDeviceObject
from bacpypes.object import get_datatype
from bacpypes.pdu import Address
from bacpypes.primitivedata import Unsigned, ObjectIdentifier
_root_logger.setLevel(_root_logger_level)

from nio import Block, Signal
from nio.block.mixins.enrich.enrich_signals import EnrichSignals
from nio.properties import Property, IntProperty, StringProperty, \
                           VersionProperty
from nio.util.threading import spawn


class ReadProperty(EnrichSignals, Block):

    address = StringProperty(title='Address',
                             default='<ip_address> [/<net_mask>] [:<port>]',
                             order=10)
    object_type = StringProperty(title='Object Type', order=11)
    instance_num = IntProperty(title='Object Instance Number', order=12)
    property_id = StringProperty(title='Property', order=13)
    array_index = Property(title='Array Index (Optional)',
                           allow_none=True,
                           order=14)
    timeout = IntProperty(title='Request Timeout',
                          default=1,
                          order=20)
    my_address = StringProperty(title='My Address',
                                default='[[NIOHOST]]:47808',
                                order=21,
                                advanced=True)
    version = VersionProperty('0.1.0')

    def __init__(self):
        super().__init__()
        self.device = None
        self.application = None
        self.object_identifer = None
        self._thread = None

    def configure(self, context):
        super().configure(context)
        # object and vendor ids are required here but not used
        self.device = LocalDeviceObject(objectIdentifier=0,
                                        vendorIdentifier=0)
        self.application = BIPSimpleApplication(self.device, self.my_address())
        # kwargs to run suppress warnings from bacpypes logging
        kwargs = {'sigterm': None, 'sigusr1': None}
        self._thread = spawn(run, **kwargs)
        self.logger.debug('BACNet/IP Application started at {}'\
                          .format(self.my_address()))

    def process_signals(self, signals):
        outgoing_signals = []
        for signal in signals:
            value = self._read(self.address(signal),
                               self.object_type(signal),
                               self.instance_num(signal),
                               self.property_id(signal),
                               self.array_index(signal))
            new_signal_dict = {
                'value': value,
                'details': {
                    'address': self.address(signal),
                    'object_type': self.object_type(signal),
                    'instance_num': self.instance_num(signal),
                    'property_id': self.property_id(signal),
                    'array_index': self.array_index(signal),
                },
            }
            new_signal = self.get_output_signal(new_signal_dict, signal)
            outgoing_signals.append(new_signal)
        self.notify_signals(outgoing_signals)

    def stop(self):
        self.logger.debug('Stopping application at {}'\
                          .format(self.my_address()))
        stop()
        self._thread.join()
        super().stop()

    def _read(self, address, object_type, instance_num, property_id, index):
        object_id = '{}:{}'.format(object_type, instance_num)
        object_id = ObjectIdentifier(object_id).value
        datatype = get_datatype(object_id[0], property_id)
        if not datatype:
            raise ValueError('Invalid property {} for object {}'\
                             .format(property_id, object_id))
        request = ReadPropertyRequest(objectIdentifier=object_id,
                                      propertyIdentifier=property_id)
        if index is not None:
            request.propertyArrayIndex = index
            idx_str = '[{}]'.format(index)
        else:
            idx_str = ''
        request.pduDestination = Address(address)
        iocb = IOCB(request)
        self.application.request_io(iocb)
        self.logger.debug('Request for {}:{}{} sent to {}'\
                          .format(object_type, instance_num, idx_str, address))
        iocb.wait(timeout=self.timeout())
        if iocb.ioError:
            raise Exception(iocb.ioError)
        elif iocb.ioResponse:
            apdu = iocb.ioResponse
            if not isinstance(apdu, ReadPropertyACK):
                raise Exception('Expected ReadPropertyACK, got {}'\
                                .format(apdu.__class__.__name__))
            datatype = get_datatype(apdu.objectIdentifier[0],
                                    apdu.propertyIdentifier)
            if not datatype:
                raise TypeError('Unknown datatype in response')
            if apdu.propertyArrayIndex is not None and \
                    issubclass(datatype, Array):
                # special case for arrays
                if apdu.propertyArrayIndex == 0:
                    value = apdu.propertyValue.cast_out(Unsigned)
                else:
                    value = apdu.propertyValue.cast_out(datatype.subtype)
            else:
                value = apdu.propertyValue.cast_out(datatype)
            return value
        else:
            raise Exception('Request to {} timed out after {} seconds'\
                             .format(address, self.timeout()))
