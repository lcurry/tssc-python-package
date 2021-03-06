import sh
import sys

import unittest
from unittest.mock import patch
from testfixtures import TempDirectory

from tssc.step_implementers.push_container_image import Skopeo

from test_utils import *

class TestStepImplementerPushContainerImageSkopeo(unittest.TestCase):

    def test_create_container_image_default_missing_args(self):
        with TempDirectory() as temp_dir:
            config = {
                'tssc-config': {}
            }
            expected_step_results = {'tssc-results': {'push-container-image': {'image-tag': ''}}}
    
            with self.assertRaisesRegex(
                    ValueError,
                    r'Key \(source\) must have non-empty value in the step configuration|Key \(destination\) must have non-empty value in the step configuration'):
                run_step_test_with_result_validation(temp_dir, 'push-container-image', config, expected_step_results)
    
    def test_push_container_image_specify_skopeo_implementer_missing_args(self):
        with TempDirectory() as temp_dir:
            config = {
                'tssc-config': {    
                    'push-container-image': {
                        'implementer': 'Skopeo',
                        'config': {}
                    }
                }
            }
            expected_step_results = {'tssc-results': {'push-container-image': {'image-tag': ''}}}

            with self.assertRaisesRegex(
                    ValueError,
                    r'Key \(source\) must have non-empty value in the step configuration|Key \(destination\) must have non-empty value in the step configuration'):
                run_step_test_with_result_validation(temp_dir, 'push-container-image', config, expected_step_results)
    
    @patch('sh.skopeo', create=True)
    def test_create_container_image_specify_skopeo_implementer_invalid_arguments(self, skopeo_mock):
        with TempDirectory() as temp_dir:
            config = {
                'tssc-config': {    
                    'push-container-image': {
                        'implementer': 'Skopeo',
                        'config': {
                            'destination' : 'docker-archive:' + temp_dir.path + '/image.tar' 
                        }
                    }
                }
            }
    
            with self.assertRaisesRegex(
                    RuntimeError,
                    r'Missing image tar .*'):
                run_step_test_with_result_validation(temp_dir, 'push-container-image', config, [])
    
    @patch('sh.skopeo', create=True)
    def test_create_container_image_specify_skopeo_implementer_valid_arguments(self, skopeo_mock):
        with TempDirectory() as temp_dir:
            source = 'docker://quay.io/tssc/tssc-base:latest'
            destination = '{path}//image.tar'.format(path=temp_dir.path)
            version = '1.0-69442c8'
            temp_dir.makedir('tssc-results')
            temp_dir.write(
                'tssc-results/tssc-results.yml',
                bytes(
                    '''tssc-results:
                  generate-metadata:
                    image-tag: {version}
                  create-container-image:
                    image-tar-file: {destination}
                '''.format(version=version, destination=destination),
                    'utf-8')
                )
            config = {
                'tssc-config': {    
                    'push-container-image': {
                        'implementer': 'Skopeo',
                        'config': {
                            'source' : source,
                            'destination' : destination
                        }
                    }
                }
            }
            
            expected_step_results = {'tssc-results': { 'create-container-image': {'image-tar-file': destination}, 'generate-metadata': {'image-tag': version }, 'push-container-image': {'image-tag': "{destination}:{version}".format(destination=destination, version=version)}}}
            run_step_test_with_result_validation(temp_dir, 'push-container-image', config, expected_step_results)
            skopeo_mock.copy.assert_called_once_with(
                '--src-tls-verify=true',
                '--dest-tls-verify=true',
                "docker-archive:{destination}".format(destination=destination),
                "{destination}:{version}".format(destination=destination, version=version),
                _out=sys.stdout
            )

    @patch('sh.skopeo', create=True)
    def test_push_container_image_specify_skopeo_implementer_skopeo_error(self, skopeo_mock):
        with TempDirectory() as temp_dir:
            source = 'docker://quay.io/tssc/tssc-base:latest'
            destination = '{path}/image.tar'.format(path=temp_dir.path)
            version = '1.0-69442c8'
            temp_dir.makedir('tssc-results')
            temp_dir.write(
                'tssc-results/tssc-results.yml',
                bytes(
                    '''tssc-results:
                  generate-metadata:
                    image-tag: {version}
                  create-container-image:
                    image-tar-file: image.tar
                '''.format(version=version),
                    'utf-8')
                )
    
            config = {
                'tssc-config': {    
                    'push-container-image': {
                        'implementer': 'Skopeo',
                        'config': {
                            'source' : source,
                            'destination' : destination
                        }
                    }
                },
                'generate-metadata': {
                        'implementer': 'Maven',
                        'config' : {}
                    }
            }
            expected_step_results = {'tssc-results': {'create-container-image': {'image-tar-file': 'image.tar'},'generate-metadata': {'image-tag': version},
                                     'push-container-image': {'image-tag':"{destination}:{version}".format(destination=destination, version=version)}}}

            sh.skopeo.copy.side_effect = sh.ErrorReturnCode('skopeo', b'mock stdout', b'mock error about skopeo runtime')
            with self.assertRaisesRegex(
                    RuntimeError,
                    r'Error invoking .*'):
                    run_step_test_with_result_validation(temp_dir, 'push-container-image', config, expected_step_results)
    
