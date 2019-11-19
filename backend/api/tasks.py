# -*- coding: utf-8 -*-
"""
@author: wangshujing
"""
from .models import HistoryRecord
from rq import get_current_job
from django_rq import job
from .ienum import FILETYPE
from django.conf import settings
from .video import video
import requests
import json

def get_two_float(f_str, n):
    f_str = str(f_str)      # f_str = '{}'.format(f_str) 也可以转换为字符串
    a, b, c = f_str.partition('.')
    c = (c+"0"*n)[:n]       # 如论传入的函数有几位小数，在字符串后面都添加n为小数0
    return ".".join([a, c])


def UpdateHistoryRecord(serializer, filetype, result, maxtype, violence, porn):
    file_id = serializer.id
    file_type = filetype
    screenshot_url = ""
    duration = ""

    if filetype == FILETYPE.Image.value:
        file_name = serializer.image.name.split('/')[1]
        file_url = settings.FILE_URL + serializer.image.url
    elif file_type == FILETYPE.Video.value:
        file_name = serializer.video.name.split('/')[1]
        file_url = settings.FILE_URL + serializer.video.url
        screenshot_url = result["screenshot_url"]
        duration = result["duration"]
    elif file_type == FILETYPE.Audio.value:
        file_name = serializer.speech.name.split('/')[1]
        file_url = settings.FILE_URL + serializer.speech.url
    elif file_type == FILETYPE.Text.value:
        file_name = serializer.text.name.split('/')[1]
        file_url = settings.FILE_URL + serializer.text.url
    elif file_type == FILETYPE.Content.value:
        file_name = ""
        file_url = ""
    else:
        file_name = "other"
        file_url = "other"

    inspection_result = result

    violence_percent = "0"
    violence_sensitivity_level = "0"
    if violence is not None:
        violence_percent = get_two_float(float(violence), 2)
        if (float(violence) < 0.5):
            violence_sensitivity_level = "0"
        if (float(violence) >= 0.5 and float(violence) <= 0.9):
            violence_sensitivity_level = "1"
        if (float(violence) > 0.9):
            violence_sensitivity_level = "2"

    porn_percent = "0"
    porn_sensitivity_level = "0"
    if porn is not None:
        porn_percent = get_two_float(float(porn), 2)
        if (float(porn) < 0.5):
            porn_sensitivity_level = "0"
        if (float(porn) >= 0.5 and float(porn) <= 0.9):
            porn_sensitivity_level = "1"
        if (float(porn) > 0.9):
            porn_sensitivity_level = "2"

    max_sensitivity_type = maxtype
    max_sensitivity_percent = "0.00"

    content = ""
    web_text = ""
    app_text = ""
    if maxtype == 'violence':
        max_sensitivity_level = violence_sensitivity_level
        max_sensitivity_percent = violence_percent
    elif maxtype == 'porn':
        max_sensitivity_level = porn_sensitivity_level
        max_sensitivity_percent = porn_percent
    elif maxtype == 'violence_porn':
        max_sensitivity_level = violence_sensitivity_level
        max_sensitivity_percent = violence_percent
    elif maxtype == 'text' and file_type == FILETYPE.Text.value:
        max_sensitivity_level = None
        max_sensitivity_percent = "0.00"
        content = result["text_content"]
        web_text = result["sensitive_info"]["web_text"]
        app_text = result["sensitive_info"]["app_text"]
    elif maxtype == 'text' and file_type == FILETYPE.Content.value:
        max_sensitivity_level = None
        max_sensitivity_percent = "0.00"
        content = serializer.text
        web_text = result["web_text"]
        app_text = result["app_text"]
    elif maxtype == 'ocr':
        max_sensitivity_level = None
        max_sensitivity_percent = "0.00"
        content = result
    elif maxtype == 'audio':
        max_sensitivity_level = None
        max_sensitivity_percent = "0.00"
        content = result['text']
    else:
        max_sensitivity_level = None
        max_sensitivity_percent = "0.00"

    process_status = 2
    system_id = serializer.system_id
    channel_id = serializer.channel_id
    user_id = serializer.user_id

    if result.get('serial_number') is not None:
        serial_number = result["serial_number"]
        iHistoryRecord = HistoryRecord.objects.get(serial_number=serial_number)
        iHistoryRecord.inspection_result = inspection_result
        iHistoryRecord.max_sensitivity_type = max_sensitivity_type
        iHistoryRecord.max_sensitivity_level = max_sensitivity_level
        iHistoryRecord.max_sensitivity_percent = max_sensitivity_percent
        iHistoryRecord.violence_percent = violence_percent
        iHistoryRecord.porn_sensitivity_level = porn_sensitivity_level
        iHistoryRecord.content = content
        iHistoryRecord.web_text = web_text
        iHistoryRecord.app_text = app_text
        iHistoryRecord.process_status = 2
        iHistoryRecord.screenshot_url = screenshot_url
        iHistoryRecord.duration = duration
        iHistoryRecord.save()
    else:
        serial_number = int(time.time())
        HistoryRecord.objects.create(
            file_id=file_id, file_name=file_name,
            file_url=file_url, file_type=file_type,
            inspection_result=inspection_result, max_sensitivity_type=max_sensitivity_type,
            max_sensitivity_level=max_sensitivity_level, max_sensitivity_percent=max_sensitivity_percent, violence_percent=violence_percent,
            violence_sensitivity_level=violence_sensitivity_level, porn_percent=porn_percent,
            porn_sensitivity_level=porn_sensitivity_level, content=content,
            web_text=web_text, app_text=app_text, process_status=process_status,
            system_id=system_id, channel_id=channel_id, user_id=user_id,
            screenshot_url=screenshot_url, duration=duration
        )


@job
def task_check_video(iserializer, serial_number):
    file_path = iserializer.video.path
    orientation = iserializer.orientation

    # 多进程情况下不可用
    # resultMap = video().check_video_V2(file_path, orientation, serial_number)

    URL = settings.LOCAL_SERVER + '/api/v1/video/get_video_inspection/'
    data = {
        'csrfmiddlewaretoken': (None, str('')),
        'video': (None, str('')),
        'video_url':(None, str(iserializer.data['video_url'])),
        'system_id': (None, str('99')),
        'channel_id': (None, str('15')),
        'sync': (None, str('1')),
        'is_task': (None, str('1')),
        'serial_number': (None, str(iserializer.data['serial_number']))
    }
    try:
        resp = requests.post(URL, 
                files=data,
                params={},
                verify=False,
                timeout=3600)
        # print (resp.status_code)
        # print (resp.request.url)
        # print (resp.request.body)
        # print (resp.text)
        jsonStr = json.loads(resp.text)
        resultMap = jsonStr['data']
        ret = 0
        msg = "成功"
        # 更新历史记录
        UpdateHistoryRecord(iserializer, FILETYPE.Video.value,
                            resultMap, resultMap['max_sensitivity_type'],
                            resultMap['violence_percent'], resultMap['porn_percent'])
    except requests.Timeout:
        pass
    except requests.ConnectionError:
        pass

    

