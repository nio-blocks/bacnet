from unittest.mock import patch, MagicMock
# bacpypes hijacks _root logger, take it back!
import logging
_root_logger = logging.getLogger()
_root_logger_level = _root_logger.level
from bacpypes.apdu import ReadPropertyACK
from bacpypes.local.device import LocalDeviceObject
_root_logger.setLevel(_root_logger_level)
from nio.block.terminals import DEFAULT_TERMINAL
from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from ..read_property_block import BACNetReadProperty


@patch(BACNetReadProperty.__module__ + '.Address')
@patch(BACNetReadProperty.__module__ + '.get_datatype')
@patch(BACNetReadProperty.__module__ + '.ObjectIdentifier')
@patch(BACNetReadProperty.__module__ + '.ReadPropertyRequest')
@patch(BACNetReadProperty.__module__ + '.IOCB')
@patch(BACNetReadProperty.__module__ + '.BIPSimpleApplication')
@patch(BACNetReadProperty.__module__ + '.run')
@patch(BACNetReadProperty.__module__ + '.stop')
class TestReadProperty(NIOBlockTestCase):

    def test_read_property(self,
                             mock_stop,
                             mock_run,
                             mock_app,
                             mock_iocb,
                             mock_request,
                             mock_identifier,
                             mock_get_datatype,
                             mock_address):
        """ A ReadProperty request is sent for every signal processed."""
        config = {
            'address': 'some_ip:some_port',
            'object_type': 'some_type',
            'instance_num': 42,
            'property_id': 'some_property',
            'array_index': None,
            'enrich': {
                'exclude_existing': False,
            },
        }
        req_obj = mock_request.return_value = MagicMock()
        obj = mock_identifier.return_value = MagicMock()
        obj_id = obj.value = MagicMock()
        mock_resp = ReadPropertyACK()
        mock_resp.objectIdentifier = [
            config['object_type'], config['instance_num']]
        mock_resp.propertyValue = MagicMock()
        mock_resp.propertyValue.cast_out.return_value = 'w00t'
        test_iocb = mock_iocb.return_value = MagicMock(ioError=None,
                                                       ioResponse=mock_resp)
        test_app = mock_app.return_value = MagicMock()

        blk = BACNetReadProperty()
        self.configure_block(blk, config)

        blk.start()
        self.assertTrue(isinstance(blk.device, LocalDeviceObject))
        mock_app.assert_called_once_with(blk.device, blk.my_address())
        # kwargs to run suppress warnings from bacpypes logging
        mock_run.assert_called_once_with(sigterm=None, sigusr1=None)
        blk.process_signals([Signal({'pi': 3.14})])
        mock_request.assert_called_once_with(
            objectIdentifier=obj_id, propertyIdentifier=config['property_id'])
        mock_iocb.assert_called_once_with(req_obj)
        test_app.request_io.assert_called_once_with(test_iocb)
        test_iocb.wait.assert_called_once_with(timeout=blk.timeout())

        blk.stop()
        mock_stop.assert_called_once_with()
        self.assert_num_signals_notified(1)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {
                'pi': 3.14,
                'value': 'w00t',
                'details': {
                    'address': config['address'],
                    'object_type': config['object_type'],
                    'instance_num': config['instance_num'],
                    'property_id': config['property_id'],
                    'array_index': config['array_index'],
                },
            },
        )

    def test_expressions(self,
                         mock_stop,
                         mock_run,
                         mock_app,
                         mock_iocb,
                         mock_request,
                         mock_identifier,
                         mock_get_datatype,
                         mock_address):
        """ Block properties evaluate with a signal"""
        config = {
            'address': '{{ $address }}',
            'object_type': '{{ $object_type }}',
            'instance_num': '{{ $instance_num }}',
            'property_id': '{{ $property_id }}',
            'array_index': '{{ $array_index }}',
        }
        signal_dict = {
            'address': 'some_ip:some_port',
            'object_type': 'some_type',
            'instance_num': 42,
            'property_id': 'some_property',
            'array_index': None,
        }
        mock_resp = ReadPropertyACK()
        mock_resp.objectIdentifier = [
            signal_dict['object_type'], signal_dict['instance_num']]
        mock_resp.propertyValue = MagicMock()
        mock_resp.propertyValue.cast_out.return_value = 'w00t'
        test_iocb = mock_iocb.return_value = MagicMock(ioError=None,
                                                       ioResponse=mock_resp)

        blk = BACNetReadProperty()
        self.configure_block(blk, config)
        blk.start()
        blk.process_signals([Signal(signal_dict)])
        blk.stop()
        self.assert_num_signals_notified(1)
        self.assertDictEqual(
            self.last_notified[DEFAULT_TERMINAL][0].to_dict(),
            {
                'value': 'w00t',
                'details': {
                    'address': signal_dict['address'],
                    'object_type': signal_dict['object_type'],
                    'instance_num': signal_dict['instance_num'],
                    'property_id': signal_dict['property_id'],
                    'array_index': signal_dict['array_index'],
                },
            },
        )
