# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:40
# @Desc    : 微博爬虫 API 请求 client

import asyncio
import copy
import json
import random
import re
import time
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import parse_qs, unquote, urlencode

import httpx
from httpx import Response
from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_exponential, wait_fixed

import config
from notification.qy_weixin import notify_final_error
from tools import utils

from .exception import DataFetchError
from .field import SearchType
from store import weibo as weibo_store


class WeiboClient:

    def __init__(
        self,
        timeout=60,  # 若开启爬取媒体选项，weibo 的图片需要更久的超时时间
        proxy=None,
        *,
        headers: Dict[str, str],
        playwright_page: Page,
        cookie_dict: Dict[str, str],
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://m.weibo.cn"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self._image_agent_host = "https://i1.wp.com/"

    @retry(stop=stop_after_attempt(5),
           wait=wait_exponential(multiplier=2, min=5, max=300),
           retry_error_callback=notify_final_error)
    async def request(self, method, url, **kwargs) -> Union[Response, Dict]:
        enable_return_response = kwargs.pop("return_response", False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if enable_return_response:
            return response

        try:
            data: Dict = response.json()
        except json.decoder.JSONDecodeError:
            # issue: #771 搜索接口会报错432， 多次重试 + 更新 h5 cookies
            utils.logger.error(
                f"[WeiboClient.request] request {method}:{url} err code: {response.status_code} res:{response.text}")
            await self.playwright_page.goto(self._host)
            await asyncio.sleep(2)
            await self.update_cookies(browser_context=self.playwright_page.context)
            raise DataFetchError(f"get response code error: {response.status_code}")

        ok_code = data.get("ok")
        if ok_code == 0:  # response error
            utils.logger.error(f"[WeiboClient.request] request {method}:{url} err, res:{data}")
            # raise DataFetchError(data.get("msg", "response error"))
        elif ok_code != 1:  # unknown error
            utils.logger.error(f"[WeiboClient.request] request {method}:{url} err, res:{data}")
            raise DataFetchError(data.get("msg", "unknown error"))
        else:  # response right
            return data.get("data", {})

    async def get(self, uri: str, params=None, headers=None, **kwargs) -> Union[Response, Dict]:
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")

        if headers is None:
            headers = self.headers
        return await self.request(method="GET", url=f"{self._host}{final_uri}", headers=headers, **kwargs)

    async def post(self, uri: str, data: dict) -> Dict:
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        return await self.request(method="POST", url=f"{self._host}{uri}", data=json_str, headers=self.headers)

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("[WeiboClient.pong] Begin pong weibo...")
        ping_flag = False
        try:
            uri = "/api/config"
            resp_data: Dict = await self.request(method="GET", url=f"{self._host}{uri}", headers=self.headers)
            if resp_data.get("login"):
                ping_flag = True
            else:
                utils.logger.error(f"[WeiboClient.pong] cookie may be invalid and again login...")
        except Exception as e:
            utils.logger.error(f"[WeiboClient.pong] Pong weibo failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def update_cookies(self, browser_context: BrowserContext, urls: Optional[List[str]] = None):
        """
        Update cookies from browser context
        :param browser_context: Browser context
        :param urls: Optional list of URLs to filter cookies (e.g., ["https://m.weibo.cn"])
                     If provided, only cookies for these URLs will be retrieved
        """
        if urls:
            cookies = await browser_context.cookies(urls=urls)
            utils.logger.info(f"[WeiboClient.update_cookies] Updating cookies for specific URLs: {urls}")
        else:
            cookies = await browser_context.cookies()
            utils.logger.info("[WeiboClient.update_cookies] Updating all cookies")

        cookie_str, cookie_dict = utils.convert_cookies(cookies)
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict
        utils.logger.info(
            f"[WeiboClient.update_cookies] Cookie updated successfully, total: {len(cookie_dict)} cookies")

    async def get_note_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        search_type: SearchType = SearchType.DEFAULT,
    ) -> Dict:
        """
        search note by keyword
        :param keyword: 微博搜搜的关键词
        :param page: 分页参数 -当前页码
        :param search_type: 搜索的类型，见 weibo/filed.py 中的枚举SearchType
        :return:
        """
        uri = "/api/container/getIndex"
        containerid = f"100103type={search_type.value}&q={keyword}"
        params = {
            "containerid": containerid,
            "page_type": "searchall",
            "page": page,
        }
        return await self.get(uri, params)

    async def get_note_comments(self, mid_id: str, max_id: int, max_id_type: int = 0) -> Dict:
        """get notes comments
        :param mid_id: 微博ID
        :param max_id: 分页参数ID
        :param max_id_type: 分页参数ID类型
        :return:
        """
        uri = "/comments/hotflow"
        params = {
            "id": mid_id,
            "mid": mid_id,
            "max_id_type": max_id_type,
        }
        if max_id > 0:
            params.update({"max_id": max_id})
        referer_url = f"https://m.weibo.cn/detail/{mid_id}"
        headers = copy.copy(self.headers)
        headers["Referer"] = referer_url

        return await self.get(uri, params, headers=headers)

    async def get_note_all_comments(
        self,
        note_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ):
        """
        get note all comments include sub comments
        :param note_id:
        :param crawl_interval:
        :param callback:
        :param max_count:
        :return:
        """
        result = []
        is_end = False
        max_id = -1
        max_id_type = 0
        while not is_end and len(result) < max_count:
            comments_res = await self.get_note_comments(note_id, max_id, max_id_type)
            max_id: int = comments_res.get("max_id")
            max_id_type: int = comments_res.get("max_id_type")
            comment_list: List[Dict] = comments_res.get("data", [])
            is_end = max_id == 0
            if len(result) + len(comment_list) > max_count:
                comment_list = comment_list[:max_count - len(result)]
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(note_id, comment_list)
            await asyncio.sleep(crawl_interval)
            result.extend(comment_list)
            sub_comment_result = await self.get_comments_all_sub_comments(note_id, comment_list, callback)
            result.extend(sub_comment_result)
        return result

    @staticmethod
    async def get_comments_all_sub_comments(
        note_id: str,
        comment_list: List[Dict],
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        获取评论的所有子评论
        Args:
            note_id:
            comment_list:
            callback:

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(f"[WeiboClient.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled")
            return []

        res_sub_comments = []
        for comment in comment_list:
            sub_comments = comment.get("comments")
            if sub_comments and isinstance(sub_comments, list):
                await callback(note_id, sub_comments)
                res_sub_comments.extend(sub_comments)
        return res_sub_comments

    async def get_note_info_by_id(self, note_id: str) -> Dict:
        """
        根据帖子ID获取详情
        :param note_id:
        :return:
        """
        url = f"{self._host}/detail/{note_id}"
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request("GET", url, timeout=self.timeout, headers=self.headers)
            if response.status_code != 200:
                raise DataFetchError(f"get weibo detail err: {response.text}")
            match = re.search(r'var \$render_data = (\[.*?\])\[0\]', response.text, re.DOTALL)
            if match:
                render_data_json = match.group(1)
                render_data_dict = json.loads(render_data_json)
                note_detail = render_data_dict[0].get("status")
                note_item = {"mblog": note_detail}
                return note_item
            else:
                utils.logger.info(f"[WeiboClient.get_note_info_by_id] 未找到$render_data的值")
                return dict()

    async def get_note_image(self, image_url: str) -> bytes:
        image_url = image_url[8:]  # 去掉 https://
        sub_url = image_url.split("/")
        image_url = ""
        for i in range(len(sub_url)):
            if i == 1:
                image_url += "large/"  # 都获取高清大图
            elif i == len(sub_url) - 1:
                image_url += sub_url[i]
            else:
                image_url += sub_url[i] + "/"
        # 微博图床对外存在防盗链，所以需要代理访问
        # 由于微博图片是通过 i1.wp.com 来访问的，所以需要拼接一下
        final_uri = (f"{self._image_agent_host}"
                     f"{image_url}")
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            try:
                response = await client.request("GET", final_uri, timeout=self.timeout)
                response.raise_for_status()
                if not response.reason_phrase == "OK":
                    utils.logger.error(f"[WeiboClient.get_note_image] request {final_uri} err, res:{response.text}")
                    return None
                else:
                    return response.content
            except httpx.HTTPError as exc:  # some wrong when call httpx.request method, such as connection error, client error, server error or response status code is not 2xx
                # 保留原始异常类型名称，以便开发者调试
                utils.logger.error(
                    f"[DouYinClient.get_aweme_media] {exc.__class__.__name__} for {exc.request.url} - {exc}")
                return None

    async def get_creator_container_info(self, creator_id: str) -> Dict:
        """
        获取用户的容器ID, 容器信息代表着真实请求的API路径
            fid_container_id：用户的微博详情API的容器ID
            lfid_container_id：用户的微博列表API的容器ID
        Args:
            creator_id:

        Returns: {

        """
        response = await self.get(f"/u/{creator_id}", return_response=True)
        m_weibocn_params = response.cookies.get("M_WEIBOCN_PARAMS")
        if not m_weibocn_params:
            raise DataFetchError("get containerid failed")
        m_weibocn_params_dict = parse_qs(unquote(m_weibocn_params))
        return {"fid_container_id": m_weibocn_params_dict.get("fid", [""])[0], "lfid_container_id": m_weibocn_params_dict.get("lfid", [""])[0]}

    async def get_creator_info_by_id(self, creator_id: str) -> Dict:
        """
        根据用户ID获取用户详情
        Args:
            creator_id:

        Returns:

        """
        uri = "/api/container/getIndex"
        containerid = f"100505{creator_id}"
        params = {
            "jumpfrom": "weibocom",
            "type": "uid",
            "value": creator_id,
            "containerid": containerid,
        }
        user_res = await self.get(uri, params)
        return user_res

    async def get_notes_by_creator(
        self,
        creator: str,
        container_id: str,
        since_id: str = "0",
    ) -> Dict:
        """
        获取博主的笔记
        Args:
            creator: 博主ID
            container_id: 容器ID
            since_id: 上一页最后一条笔记的ID
        Returns:

        """

        uri = "/api/container/getIndex"
        params = {
            "jumpfrom": "weibocom",
            "type": "uid",
            "value": creator,
            "containerid": container_id,
            "since_id": since_id,
        }
        return await self.get(uri, params)

    async def get_user_last_ts(self, creator_id: str) -> int:
        """
        获取用户的最后修改时间戳
        Args:
            creator_id:

        Returns:

        """
        creator_info = await weibo_store.WeibostoreFactory.create_store().get_creator(creator_id)
        user_last_ts = 0
        if creator_info:
            user_last_ts = (creator_info.last_modify_ts or 0) // 1000
        user_last_ts = user_last_ts or utils.get_unix_timestamp() - 60 * 60 * 1
        return user_last_ts

    async def get_all_notes_by_creator_id(
        self,
        creator_id: str,
        container_id: str,
        crawl_interval: float = 1.0,
    ) -> List[Dict]:
        """
        获取指定用户下的所有发过的帖子，该方法会一直查找一个用户下的所有帖子信息
        Args:
            creator_id:
            container_id:
            crawl_interval:
            callback:

        Returns:

        """
        result = []
        notes_has_more = True
        since_id = ""
        last_modify_ts = await self.get_user_last_ts(creator_id)
        crawler_total_count = 0
        while notes_has_more:
            utils.logger.info(
                f"[WeiboClient.get_all_notes_by_creator] Fetching notes for user_id:{creator_id} with since_id:{since_id} ...")
            notes_res = await self.get_notes_by_creator(creator_id, container_id, since_id)
            if not notes_res:
                utils.logger.error(
                    f"[WeiboClient.get_notes_by_creator] The current creator may have been banned by xhs, so they cannot access the data.")
                break
            since_id = notes_res.get("cardlistInfo", {}).get("since_id", "0")
            if "cards" not in notes_res:
                utils.logger.info(
                    f"[WeiboClient.get_all_notes_by_creator] No 'notes' key found in response: {notes_res}")
                break

            notes = notes_res["cards"]
            utils.logger.info(
                f"[WeiboClient.get_all_notes_by_creator] got user_id: {creator_id} notes len : {len(notes)}")
            notes = [note for note in notes if note.get("card_type") == 9]
            is_continue = await self.batch_update_weibo_notes(notes, last_modify_ts)
            if not is_continue or since_id == "0" or not notes:
                utils.logger.info(
                    f"[WeiboClient.get_all_notes_by_creator] Stopping fetch for user_id:{creator_id}. is_continue:{is_continue}, since_id:{since_id}, notes_len:{len(notes)}")
                break

            await asyncio.sleep(utils.human_sleep(crawl_interval))
            result.extend(notes)
            crawler_total_count += 10
            notes_has_more = notes_res.get("cardlistInfo", {}).get("total", 0) > crawler_total_count
        return result

    async def batch_update_weibo_notes(self, note_list: List[Dict], last_modify_ts: int):
        """
        Batch update weibo notes
        Args:
            note_list:
        Returns:
        """
        if not note_list:
            return
        is_continue = True
        for note_item in note_list:
            is_top, is_new = await self.parse_check(note_item, last_modify_ts)
            if not is_top and not is_new:  # 如果不是置顶且不是新发布的，就停止爬取
                is_continue = False
                break
            if is_new:
                await self.parse_note(note_item)
        return is_continue

    async def parse_check(self, note_item: Dict, last_modify_ts: int):
        """
        解析单个微博帖子的详情
        Args:
            note_item:

        Returns:

        """
        mblog: Dict = note_item.get("mblog")
        is_top, is_new = False, False
        top = mblog.get("title")
        if "置顶" in str(top):
            is_top = True
        if utils.rfc2822_to_timestamp(mblog.get("created_at")) > last_modify_ts:
            is_new = True
        return is_top, is_new

    async def parse_note(self, note_item: Dict) -> Dict:
        """
        解析单个微博帖子的详情
        Args:
            note_item:

        Returns:

        """
        mblog: Dict = note_item.get("mblog")
        user_info: Dict = mblog.get("user")
        note_id = mblog.get("id")
        clean_text = re.sub(r"<.*?>", "", mblog.get("text"))
        content_item = {
            # 微博信息
            "note_id": note_id,
            "content": clean_text,
            "create_time": utils.rfc2822_to_timestamp(mblog.get("created_at")),
            "create_date_time": str(utils.rfc2822_to_china_datetime(mblog.get("created_at"))),
            "liked_count": str(mblog.get("attitudes_count", 0)),
            "comments_count": str(mblog.get("comments_count", 0)),
            "shared_count": str(mblog.get("reposts_count", 0)),
            "last_modify_ts": utils.get_current_timestamp(),
            "note_url": f"https://m.weibo.cn/detail/{note_id}",
            "ip_location": mblog.get("region_name", "").replace("发布于 ", ""),

            "pics": await self._note_pics(mblog),
            # "live_photo": mblog.get("live_photo", []),  # TODO：暂不处理动态图片
            "media_info": mblog.get("page_info", {}).get("media_info", {}),  # TODO：暂不处理视频

            # 用户信息
            "user_id": str(user_info.get("id")),
            "nickname": user_info.get("screen_name", ""),
            "gender": '女' if user_info.get('gender') == "f" else '男',
            "profile_url": user_info.get("profile_url", ""),
            "avatar": user_info.get("profile_image_url", ""),  # TODO：用户头像是否下载
        }

        is_long = True if mblog.get("pic_num") > 9 else mblog.get("isLongText")
        if is_long:
            content_item["is_long"] = is_long
            note_detail = await self.get_note_info_by_id(note_id)
            content_item["full_text"] = re.sub(r"<.*?>", "", note_detail.get("mblog", {}).get("text", ""))
        # TODO：批量保存
        utils.logger.info(f"[store.weibo.update_weibo_note] weibo note id:{note_id}, title:{clean_text[:24]} ...")
        await weibo_store.WeibostoreFactory.create_store().store_content(content_item=content_item)

    async def _note_pics(self, mblog: Dict):
        """
        get note images
        :param mblog:
        :return:
        """
        pics = []

        note_pics = mblog.get("pics")
        if not note_pics:
            return pics
        for note_pic in note_pics:
            url = note_pic.get("url")
            if not url:
                continue
            _pic = {
                "pic_id": note_pic["pid"],
                "pic_url": url,
                "pic_path": "",
            }
            if config.ENABLE_GET_MEIDAS:
                content = await self.get_note_image(url)
                await asyncio.sleep(config.CRAWL_INTERVAL)
                # utils.logger.info(f"[WeiboCrawler._note_pics] Sleeping for {config.CRAWL_INTERVAL} seconds after fetching image")
                if content != None:
                    extension_file_name = url.split(".")[-1]
                    _pic["pic_path"] = await weibo_store.update_weibo_note_image(note_pic["pid"], content, extension_file_name)
            pics.append(_pic)
        return pics
