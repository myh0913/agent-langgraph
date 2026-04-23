# SysUserApi - currentInfo 接口文档

## 接口概述

### currentInfo（查询当前登录用户信息）

#### 基本信息
- **请求路径**：`GET /sysUser/currentInfo`
- **功能说明**：查询当前登录用户的完整认证信息，包括用户基本信息、角色列表、权限资源等
- **权限说明**：需要登录认证

#### 请求示例
```json
GET /sysUser/currentInfo

Content-Type: application/json

Authorization: Bearer {token}
```

#### 响应数据结构
```json
{
  "code": 200,
  "data": {
    "headImgUrl": "https://example.com/avatar.jpg",
    "nickname": "张三",
    "username": "zhangsan",
    "deptName": "技术部",
    "superAdmin": false,
    "userId": 123456,
    "applyModel": true,
    "configData": "{}",
    "roleList": ["管理员", "普通用户"],
    "adminWorkbench": {
      "id": 1,
      "name": "工作台名称"
    },
    "authResourceDetail": {
      "businessMenus": [],
      "systemMenus": [],
      "buttonList": []
    }
  },
  "message": "success"
}
```

#### 返回字段说明

##### UserAuthVo 字段
| 字段 | 类型 | 说明 |
|------|------|------|
| headImgUrl | String | 用户头像URL |
| nickname | String | 用户昵称 |
| username | String | 用户名 |
| deptName | String | 部门名称 |
| superAdmin | boolean | 是否超级管理员：true-是，false-否 |
| userId | Long | 用户ID |
| applyModel | boolean | 是否开启申请模式 |
| configData | String | 用户配置JSON |
| roleList | List<String> | 角色名称列表 |
| adminWorkbench | SysWorkbench | 管理员工作台配置 |
| authResourceDetail | AuthResourceDetailVo | 用户的权限资源详情 |

##### AuthResourceDetailVo 字段
| 字段 | 类型 | 说明 |
|------|------|------|
| businessMenus | Set<SysResourceVo> | 业务菜单列表 |
| systemMenus | Set<SysResourceVo> | 系统菜单列表 |
| buttonList | Set<SysButtonVo> | 按钮权限列表 |

##### SysWorkbench 字段
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 工作台ID |
| name | String | 工作台名称 |
| config | String | 工作台配置JSON |

---

## 相关接口

| 接口 | 路径 | 功能 |
|------|------|------|
| current | GET /sysUser/current | 获取移动端当前用户信息 |
| authDept | GET /sysUser/authDept | 获取当前用户有权限的部门/岗位 |
| authRole | GET /sysUser/authRole | 获取当前用户有权限的角色 |
| authUser | GET /sysUser/authUser | 获取当前用户有权限查看的用户 |

---

## 业务逻辑说明

1. 从登录上下文获取当前用户信息（LoginUserContext）
2. 调用 sysUserService.getUserAuthInfo() 获取完整的用户认证信息
3. 返回用户基本信息、角色列表、权限资源详情等
