# 采用 ErrMsg 而不是采用 exception, 一来是受到 Go 语言的影响，
# 另一方面，凡是用到 ErrMsg 的地方都是与业务逻辑密切相关并且需要向用户反馈详细错误信息的地方，
# 这些地方用 ErrMsg 更合理。 (以后会改用 pypi.org/project/result)
ErrMsg = str
"""一个描述错误内容的简单字符串，空字符串表示无错误。"""
