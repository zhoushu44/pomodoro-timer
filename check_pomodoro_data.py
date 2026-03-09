import pymysql
from datetime import datetime, timedelta

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
    
    # 查询最近7天的番茄钟数据
    print('最近7天的番茄钟数据:')
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        cursor.execute('SELECT project, count FROM pomodoro_data WHERE date = %s', (date,))
        results = cursor.fetchall()
        print(f'\n{date}:')
        if results:
            total = 0
            for project, count in results:
                print(f'  {project}: {count}')
                total += count
            print(f'  总计: {total}')
        else:
            print('  无数据')
    
    # 关闭连接
    cursor.close()
    conn.close()
except Exception as e:
    print(f'查询失败: {str(e)}')
