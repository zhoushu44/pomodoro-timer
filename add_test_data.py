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
    
    # 添加测试项目
    test_projects = ['测试项目1', '测试项目2', '测试项目3']
    print('添加测试项目:')
    for project in test_projects:
        try:
            cursor.execute('INSERT IGNORE INTO projects (name) VALUES (%s)', (project,))
            print(f'- 项目 "{project}" 已添加')
        except Exception as e:
            print(f'- 添加项目 "{project}" 失败: {str(e)}')
    
    # 添加测试番茄钟数据（最近7天）
    print('\n添加测试番茄钟数据:')
    projects = ['默认项目', '测试项目1', '测试项目2', '测试项目3']
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        for project in projects:
            # 为每个项目生成1-5个番茄钟
            import random
            count = random.randint(1, 5)
            try:
                # 检查记录是否存在
                cursor.execute('SELECT count FROM pomodoro_data WHERE date = %s AND project = %s', (date, project))
                result = cursor.fetchone()
                
                if result:
                    # 更新记录
                    cursor.execute('UPDATE pomodoro_data SET count = %s WHERE date = %s AND project = %s', (count, date, project))
                else:
                    # 插入新记录
                    cursor.execute('INSERT INTO pomodoro_data (date, project, count) VALUES (%s, %s, %s)', (date, project, count))
                print(f'- {date} {project}: {count}个番茄钟')
            except Exception as e:
                print(f'- 添加 {date} {project} 数据失败: {str(e)}')
    
    # 提交事务
    conn.commit()
    print('\n测试数据添加成功！')
    
    # 关闭连接
    cursor.close()
    conn.close()
except Exception as e:
    print(f'操作失败: {str(e)}')
