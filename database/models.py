from sqlalchemy import DateTime, create_engine, Column, Integer, Text, String, BigInteger, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class WeiboCreator(Base):
    __tablename__ = 'weibo_creator'
    id = Column(Integer, primary_key=True, comment="主键ID，自增")
    user_id = Column(String(128), unique=True, index=True, comment="微博用户ID")
    nickname = Column(String(512), comment="昵称")
    avatar = Column(Text, comment="头像URL")
    ip_location = Column(String(256), comment="IP定位信息")
    gender = Column(String(16), comment="性别")
    follows = Column(Integer, default=0, comment="关注数")
    fans = Column(String(256), default="0", comment="粉丝数")
    tag_list = Column(JSON, comment="用户标签列表")
    desc = Column(Text, comment="用户简介")
    add_ts = Column(BigInteger, comment="记录添加时间戳")
    last_modify_ts = Column(BigInteger, comment="记录最后修改时间戳")


class WeiboNote(Base):
    __tablename__ = 'weibo_note'
    id = Column(Integer, primary_key=True, comment="主键ID，自增")
    note_id = Column(BigInteger, unique=True, index=True, comment="微博帖子ID")
    user_id = Column(String(128), index=True, comment="微博用户ID")
    nickname = Column(String(512), comment="昵称")
    avatar = Column(Text, comment="头像URL")
    gender = Column(String(16), comment="性别")
    profile_url = Column(String(512), comment="用户主页URL")
    ip_location = Column(String(256), default='', comment="IP定位信息")
    add_ts = Column(BigInteger, comment="记录添加时间戳")
    last_modify_ts = Column(BigInteger, comment="记录最后修改时间戳")

    content = Column(Text, comment="微博内容摘要")
    is_long = Column(Boolean, default=False, comment="是否长微博")
    full_text = Column(Text, comment="微博完整内容")
    pics = Column(JSON, comment="图片列表")
    media_info = Column(JSON, comment="媒体信息，如视频")

    create_time = Column(BigInteger, index=True, comment="微博创建时间戳")
    create_date_time = Column(DateTime(timezone=True), index=True, comment="微博创建日期字符串")

    liked_count = Column(Integer, default=0, comment="点赞数")
    comments_count = Column(Integer, default=0, comment="评论数")
    shared_count = Column(Integer, default=0, comment="转发数")

    note_url = Column(String(512), comment="微博URL")
    source_keyword = Column(String(128), default='', comment="爬取来源关键词")


class WeiboNoteComment(Base):
    __tablename__ = 'weibo_note_comment'

    id = Column(BigInteger, primary_key=True, comment="主键ID")
    user_id = Column(String(255), comment="评论用户ID")
    nickname = Column(String(512), comment="昵称")
    avatar = Column(Text, comment="头像URL")
    gender = Column(String(16), comment="性别")

    profile_url = Column(String(512), comment="用户主页URL")
    ip_location = Column(String(256), default='', comment="IP定位信息")
    add_ts = Column(BigInteger, comment="记录添加时间戳")
    last_modify_ts = Column(BigInteger, comment="最后修改时间戳")
    comment_id = Column(BigInteger, index=True, comment="评论ID")
    note_id = Column(BigInteger, index=True, comment="所属微博ID")
    content = Column(Text, comment="评论内容")
    create_time = Column(BigInteger, comment="评论创建时间戳")
    create_date_time = Column(DateTime(timezone=True), comment="评论创建完整时间")
    comment_like_count = Column(String(512), comment="评论点赞数")
    sub_comment_count = Column(String(512), comment="子评论数")
    parent_comment_id = Column(BigInteger, comment="父评论ID，如果是一级评论则为空")


class ZhihuContent(Base):
    __tablename__ = 'zhihu_content'
    id = Column(Integer, primary_key=True)
    content_id = Column(String(64), index=True)
    content_type = Column(Text)
    content_text = Column(Text)
    content_url = Column(Text)
    question_id = Column(String(255))
    title = Column(Text)
    desc = Column(Text)
    created_time = Column(String(32), index=True)
    updated_time = Column(Text)
    voteup_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    source_keyword = Column(Text)
    user_id = Column(String(255))
    user_link = Column(Text)
    user_nickname = Column(Text)
    user_avatar = Column(Text)
    user_url_token = Column(Text)
    add_ts = Column(BigInteger)
    last_modify_ts = Column(BigInteger)


class ZhihuComment(Base):
    __tablename__ = 'zhihu_comment'
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), index=True)
    parent_comment_id = Column(String(64))
    content = Column(Text)
    publish_time = Column(String(32), index=True)
    ip_location = Column(Text)
    sub_comment_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    dislike_count = Column(Integer, default=0)
    content_id = Column(String(64), index=True)
    content_type = Column(Text)
    user_id = Column(String(64))
    user_link = Column(Text)
    user_nickname = Column(Text)
    user_avatar = Column(Text)
    add_ts = Column(BigInteger)
    last_modify_ts = Column(BigInteger)


class ZhihuCreator(Base):
    __tablename__ = 'zhihu_creator'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), unique=True, index=True)
    user_link = Column(Text)
    user_nickname = Column(Text)
    user_avatar = Column(Text)
    url_token = Column(Text)
    gender = Column(Text)
    ip_location = Column(Text)
    follows = Column(Integer, default=0)
    fans = Column(Integer, default=0)
    anwser_count = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    article_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    get_voteup_count = Column(Integer, default=0)
    add_ts = Column(BigInteger)
    last_modify_ts = Column(BigInteger)
