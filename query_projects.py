import pymysql

# 数据库连接配置
config = {
    'host': '8.163.52.51',
    'port': 13306,
    'user': 'root',
    'password': 'LFajEj6Lw7tKfZ8z',
    'database': 'pomodoro'
}

try:
    # 连接数据库
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # 查询项目列表
    cursor.execute('SELECT name FROM projects ORDER BY name')
    projects = cursor.fetchall()
    
    # 打印项目列表
    print('数据库中的项目列表:')
    if projects:
        for project in projects:
            print(f'- {project[0]}')
    else:
        print('暂无项目')
    
    # 关闭连接
    cursor.close()
    conn.close()
except Exception as e:
    print(f'查询失败: {str(e)}')
