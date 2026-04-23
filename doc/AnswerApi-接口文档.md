# AnswerApi - queryRefIndicatorAndDimensionName 接口文档

## 接口概述

### queryRefIndicatorAndDimensionName（查询指标和维度列表）

#### 基本信息
- **请求路径**：`POST /answer/queryRefIndicatorAndDimensionName`
- **功能说明**：查询所有指标和维度的名称列表，用于下拉框选择等场景
- **请求Body**：无需参数（空对象或 null）

#### 请求示例
```json
POST /answer/queryRefIndicatorAndDimensionName

Content-Type: application/json

{}
```

#### 响应数据结构
```json
{
  "code": 200,
  "data": {
    "indicator": [
      {
        "name": "销售额",
        "id": 123456,
        "group_id": 100,
        "status": 1
      }
    ],
    "dimension": [
      {
        "name": "日期",
        "id": 789012,
        "group_id": 200,
        "status": 1
      }
    ]
  },
  "message": "success"
}
```

#### 返回字段说明

##### indicator 数组元素
| 字段 | 类型 | 说明                    |
|------|------|-----------------------|
| name | String | 指标名称                  |
| id | Long | 指标ID                  |
| group_id | Long | 分组ID                  |
| status | Integer | 状态（0-未发布，1-审批中，3-已发布） |

##### dimension 数组元素
| 字段 | 类型 | 说明 |
|------|------|------|
| name | String | 维度名称 |
| id | Long | 维度ID |
| group_id | Long | 分组ID |
| status | Integer | 状态（0-未发布，1-审批中，3-已发布） |

---

## 业务逻辑说明

1. 执行指标查询 SQL，查询所有类型的指标（原子/派生/复合/事件）
2. 执行维度查询 SQL，查询所有维度
3. 将指标结果放入 map 的 "indicator" 键
4. 将维度结果放入 map 的 "dimension" 键
5. 返回组合后的结果

---

## 相关常量说明

### 指标类型 type 值
| type 值 | 说明 |
|---------|------|
| 1 | 原子指标 (t_atom_indicator) |
| 2 | 复合指标 (t_composite_indicator) |
| 3 | 派生指标 (t_derivative_indicator) |
| 6 | 事件指标 (t_event_indicator) |

### 维度类型 type 值
| type 值 | 说明 |
|---------|------|
| 10 | 维度 (t_dimension) |

---
