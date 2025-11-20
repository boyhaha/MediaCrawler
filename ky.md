## 基础命令
1. 初始化数据库
uv run main.py --init_db mysql
2. 爬取
python main.py --platform wb --lt qrcode --type creator

0 3 * * * docker exec ky-media-spider python /repo/main.py --platform wb --lt qrcode --type creator


### 待完成
1. 自动登录
   1. 登录需要点击验证码（其它登录验证：手机扫描、短信验证）
   2. 单次cookie有效期
   3. 怎么刷新token
   4. 未登录可以获取指定用户40条数据
2. 爬取指定日期后的信息
3. 图片下载 await self.get_note_images(mblog)
4. 长微博处理：全文内容获取
    is_long = True if mblog.get("pic_num") > 9 else mblog.get("isLongText")
5. 定时爬取
6. 查看数据格式是否满足要求


7. 用户头像是否下载
8. 新注册账号无since_id，
9. 批量保存采集数据, 保存到哪？
10. 有的用户设置了仅粉丝可见全部微博（1642634100/新浪科技），2小时，20条
11. 镜像瘦身

#### 反爬
新注册账号，请求30分钟后 432，cookie内容也不一样
2025-11-19 16:24:34  开始
2025-11-19 16:50     432
16:55  开始
19:56:33  需要点击验证码
20:05:14  需要点击验证码


09:24:11

cookie有效期：2025-11-18：16点左右