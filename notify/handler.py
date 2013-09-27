# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Request Handler for /notify endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import io
import json
import logging
import webapp2

from google.appengine.api import memcache
from google.appengine.api import urlfetch
# The URL Fetch library
from google.appengine.api.urlfetch import fetch

# The minidom library for XML parsing
from xml.dom.minidom import parseString

from apiclient.http import MediaIoBaseUpload
from oauth2client.appengine import StorageByKeyName

from model import Credentials
import util


class NotifyHandler(webapp2.RequestHandler):
  """Request Handler for notification pings."""

  def post(self):
    """Handles notification pings."""
    logging.info('Got a notification with payload %s', self.request.body)
    data = json.loads(self.request.body)
    userid = data['userToken']
    # TODO: Check that the userToken is a valid userToken.
    self.mirror_service = util.create_service(
        'mirror', 'v1',
        StorageByKeyName(Credentials, userid, 'credentials').get())
    if data.get('collection') == 'locations':
      self._handle_locations_notification(data)
    elif data.get('collection') == 'timeline':
      self._handle_timeline_notification(data)

  def _handle_locations_notification(self, data):
    """Handle locations notification."""
    location = self.mirror_service.locations().get(id=data['itemId']).execute()
    text = 'New location is %s, %s' % (location.get('latitude'),
                                       location.get('longitude'))
    body = {
        'text': text,
        'location': location,
        'menuItems': [{'action': 'NAVIGATE'}],
        'notification': {'level': 'DEFAULT'}
    }
    self.mirror_service.timeline().insert(body=body).execute()

  def _handle_timeline_notification(self, data):
    """Handle timeline notification."""
    for user_action in data.get('userActions', []):
      if user_action.get('type') == 'SHARE':
        # Fetch the timeline item.
        item = self.mirror_service.timeline().get(id=data['itemId']).execute()
        attachments = item.get('attachments', [])
        media = None
        if attachments:
          # Get the first attachment on that timeline item and do stuff with it.
          attachment = self.mirror_service.timeline().attachments().get(
              itemId=data['itemId'],
              attachmentId=attachments[0]['id']).execute()
          resp, content = self.mirror_service._http.request(
              attachment['contentUrl'])
          if resp.status == 200:
            media = MediaIoBaseUpload(
                io.BytesIO(content), attachment['contentType'],
                resumable=True)
          else:
            logging.info('Unable to retrieve attachment: %s', resp.status)
         #test code for xml
        url=fetch('http://agent.mtconnect.org/current')
        xml = parseString(url.content)
    
        streams = xml.getElementsByTagName("Streams")
        for stream in streams:
          #Gets the stations and cycle through them
           elements = stream.getElementsByTagName("DeviceStream")
          for element in elements:
            # Grab data from the station element
            power = element.getElementsByTagName('PowerState')[0].firstChild.data
            execution = element.getElementsByTagName('Execution')[0].firstChild.data
            spindle = element.getElementsByTagName('SpindleSpeed')[0].firstChild.data
            
            # Append the data onto the string
           
            string = """<figure><img src="http://www.itamco.com/dmg1.jpg"></figure><section><table class="text-small align-justify"><tbody><tr><td>DMG</td><td>""" + str(power) + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td></tr><tr><td>Utilization</td><td>" + str(execution) + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td></tr><tr><td>Spindle Speed</td><td>" + str(spindle) + "</td></tr></tbody></table></section>"
          
        body = {
            'text': 'Got it: %s' % item.get('text', ''),
            'html': string,
            'notification': {'level': 'DEFAULT'}
        }
        self.mirror_service.timeline().insert(
            body=body, media_body=media).execute()
        # Only handle the first successful action.
        break
      else:
        logging.info(
            "I don't know what to do with this notification: %s", user_action)


NOTIFY_ROUTES = [
    ('/notify', NotifyHandler)
]
