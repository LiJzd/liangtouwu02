# -*- coding: utf-8 -*-
"""
v1/tools/text_to_sql.py
Text-to-SQL 只读安全沙盒执行工具
"""

import logging
import re
from typing import Dict, Any, List
import sqlparse
from sqlalchemy import text

from v1.common.db import AsyncSessionLocal

logger = logging.getLogger("TextToSQL")

async def execute_readonly_sql(sql: str) -> dict:
    """
    静态 SQL 防火墙审计与只读安全沙盒执行。
    除 SELECT 外，拦截一切写与表修改操作，防御多语句与 UNION 注入。
    """
    logger.info(f"=== [SQL SandBox] 接收到查询 SQL ===\n{sql}\n==================================")
    
    cleaned_sql = sql.strip()
    
    # 1. 注入防护：校验分号，防止多语句联合执行注入
    # 校验分号数量：只允许在末尾出现至多一个分号
    if cleaned_sql.count(';') > 1 or (cleaned_sql.count(';') == 1 and not cleaned_sql.endswith(';')):
        logger.warning("[SQL SandBox] 静态审计失败: 存在多语句注入嫌疑（包含分号）")
        return {
            "success": False,
            "error": "Security check failed: Only single-statement SELECT queries are allowed."
        }
        
    # 2. UNION 注入阻断（大小写不敏感）
    if re.search(r'\bUNION\b', cleaned_sql, re.IGNORECASE):
        logger.warning("[SQL SandBox] 静态审计失败: 监测到禁止使用的 UNION 关键字")
        return {
            "success": False,
            "error": "Security check failed: UNION queries are strictly prohibited for security reasons."
        }

    # 3. 拦截任何可能修改表结构、表数据或越权的高危写关键字
    forbidden_words = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "TRUNCATE", "GRANT", "MERGE", "EXEC", "EXECUTE"]
    for word in forbidden_words:
        if re.search(r'\b' + word + r'\b', cleaned_sql, re.IGNORECASE):
            logger.warning(f"[SQL SandBox] 静态审计失败: 监测到高危写操作关键字 {word}")
            return {
                "success": False,
                "error": f"Security check failed: Query contains forbidden keyword '{word}'."
            }

    # 4. 利用 sqlparse 进行精细化语法对象类型解析校验
    try:
        parsed = sqlparse.parse(cleaned_sql)
        if not parsed:
            logger.warning("[SQL SandBox] 静态审计失败: sqlparse 无法解析此语句")
            return {
                "success": False,
                "error": "Security check failed: Invalid SQL query statement."
            }
        
        # 校验首个 Statement 类型必须是 SELECT
        if parsed[0].get_type() != 'SELECT':
            logger.warning(f"[SQL SandBox] 静态审计失败: 解析类型为 {parsed[0].get_type()}，非 SELECT")
            return {
                "success": False,
                "error": "Security check failed: Only SELECT statements are allowed."
            }
    except Exception as e:
        logger.error(f"[SQL SandBox] sqlparse 解析异常: {e}")
        return {
            "success": False,
            "error": f"Security check failed: SQL parsing error: {e}"
        }

    # 5. 安全审计通过，进入只读 MySQL 账户或只读会话执行
    logger.info("[SQL SandBox] 静态安全防火墙审计通过，进入异步沙盒只读执行...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 强制使用 SQL 只读语句执行
            result = await session.execute(text(cleaned_sql))
            columns = list(result.keys())
            rows = result.fetchall()
            
            # 将 rows 组装成 dict 格式
            data = []
            for row in rows:
                # 转换 Decimal 或 DateTime 类型为基本 Python 类型以便序列化
                row_dict = {}
                for col, val in zip(columns, row):
                    if hasattr(val, 'to_eng_string'):  # Decimal
                        row_dict[col] = float(val)
                    elif hasattr(val, 'isoformat'):    # DateTime / Date
                        row_dict[col] = val.isoformat()
                    else:
                        row_dict[col] = val
                data.append(row_dict)
                
            logger.info(f"[SQL SandBox] 数据库执行成功，召回数据 {len(data)} 条")
            return {
                "success": True,
                "columns": columns,
                "data": data
            }
        except Exception as e:
            logger.error(f"[SQL SandBox] 数据库执行报错: {e}")
            return {
                "success": False,
                "error": f"SQL execution error: {str(e)}"
            }
