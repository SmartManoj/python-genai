# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import asyncio
import time
from unittest.mock import MagicMock, patch
import pytest
from .api_client import ApiClient


@patch('genai.api_client.ApiClient._build_request')
@patch('genai.api_client.ApiClient._request')
def test_request_streamed_non_blocking(mock_request, mock_build_request):
  api_client = ApiClient(api_key='test_api_key')
  http_method = 'GET'
  path = 'test/path'
  request_dict = {'key': 'value'}

  mock_http_request = MagicMock()
  mock_build_request.return_value = mock_http_request

  def delayed_segments():
    chunks = ['{"chunk": 1}', '{"chunk": 2}', '{"chunk": 3}']
    for chunk in chunks:
      time.sleep(0.1)  # 100ms delay
      yield chunk

  mock_response = MagicMock()
  mock_response.segments.side_effect = delayed_segments
  mock_request.return_value = mock_response

  chunks = []
  start_time = time.time()
  for chunk in api_client.request_streamed(http_method, path, request_dict):
    chunks.append(chunk)
    assert len(chunks) <= 3
  end_time = time.time()

  mock_build_request.assert_called_once_with(
      http_method, path, request_dict, None
  )
  mock_request.assert_called_once_with(mock_http_request, stream=True)
  assert chunks == ['{"chunk": 1}', '{"chunk": 2}', '{"chunk": 3}']
  assert end_time - start_time > 0.3


@patch('genai.api_client.ApiClient._build_request')
@patch('genai.api_client.ApiClient._async_request')
@pytest.mark.asyncio
async def test_async_request(mock_async_request, mock_build_request):
  api_client = ApiClient(api_key='test_api_key')
  http_method = 'GET'
  path = 'test/path'
  request_dict = {'key': 'value'}

  mock_http_request = MagicMock()
  mock_build_request.return_value = mock_http_request

  class MockResponse:

    def __init__(self, text):
      self.text = text

  async def delayed_response(http_request, stream):
    await asyncio.sleep(0.1)  # 100ms delay
    return MockResponse('value')

  mock_async_request.side_effect = delayed_response

  async_coroutine1 = api_client.async_request(http_method, path, request_dict)
  async_coroutine2 = api_client.async_request(http_method, path, request_dict)
  async_coroutine3 = api_client.async_request(http_method, path, request_dict)

  start_time = time.time()
  results = await asyncio.gather(
      async_coroutine1, async_coroutine2, async_coroutine3
  )
  end_time = time.time()

  mock_build_request.assert_called_with(http_method, path, request_dict, None)
  assert mock_build_request.call_count == 3
  mock_async_request.assert_called_with(
      http_request=mock_http_request, stream=False
  )
  assert mock_async_request.call_count == 3
  assert results == ['value', 'value', 'value']
  assert 0.1 <= end_time - start_time < 0.15


@patch('genai.api_client.ApiClient._build_request')
@patch('genai.api_client.ApiClient._async_request')
@pytest.mark.asyncio
async def test_async_request_streamed_non_blocking(
    mock_async_request, mock_build_request
):
  api_client = ApiClient(api_key='test_api_key')
  http_method = 'GET'
  path = 'test/path'
  request_dict = {'key': 'value'}

  mock_http_request = MagicMock()
  mock_build_request.return_value = mock_http_request

  class MockResponse:

    def __init__(self, segments):
      self._segments = segments

    # should mock async generator here but source code combines sync and async streaming in one segment method.
    # TODO: fix the above
    def segments(self):
      for segment in self._segments:
        time.sleep(0.1)  # 100ms delay
        yield segment

  async def delayed_response(http_request, stream):
    return MockResponse(['{"chunk": 1}', '{"chunk": 2}', '{"chunk": 3}'])

  mock_async_request.side_effect = delayed_response

  chunks = []
  start_time = time.time()
  async for chunk in api_client.async_request_streamed(
      http_method, path, request_dict
  ):
    chunks.append(chunk)
    assert len(chunks) <= 3
  end_time = time.time()

  mock_build_request.assert_called_once_with(
      http_method, path, request_dict, None
  )
  mock_async_request.assert_called_once_with(
      http_request=mock_http_request, stream=True
  )
  assert chunks == ['{"chunk": 1}', '{"chunk": 2}', '{"chunk": 3}']
  assert end_time - start_time > 0.3