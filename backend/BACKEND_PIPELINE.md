# Backend Pipeline

1. 启动 perception 监听流程，收集 raw_records，放到内存里面的一个滑动窗口存储中（临时存储，超出窗口时间的数据被自动删除）
2. 每隔 processing_interval 的时间，会把最近 processing_interval 时间内的 raw_records 进行 filter，然后 parse 成 event，对于这个 event 再调用 LLM api 进行 summarize
3. event 按照时间会排成一个 list，每有一个新的 event，都会和上一个activity（如果没有 activity 就直接创建一个 activity）一起给 LLM api 判断是 merge 还是 new，activity 会存到 SQLite 当中
4. 监听流程形成循环，直到用户发送停止指令