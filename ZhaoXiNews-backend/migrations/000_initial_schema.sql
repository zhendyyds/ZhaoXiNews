-- MySQL 8+ schema. Run against the database configured for ZhaoXiNews.

CREATE TABLE IF NOT EXISTS `news_category` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '分类ID',
  `name` varchar(50) NOT NULL COMMENT '分类名称',
  `sort_order` int NOT NULL DEFAULT '0' COMMENT '排序顺序',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_UNIQUE` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='新闻分类表';

CREATE TABLE IF NOT EXISTS `news` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '新闻ID',
  `title` varchar(255) NOT NULL COMMENT '新闻标题',
  `description` varchar(500) DEFAULT NULL COMMENT '新闻简介',
  `content` text NOT NULL COMMENT '新闻内容',
  `image` varchar(255) DEFAULT NULL COMMENT '封面图片URL',
  `author` varchar(50) DEFAULT NULL COMMENT '作者',
  `category_id` int unsigned NOT NULL COMMENT '分类ID',
  `views` int unsigned NOT NULL DEFAULT '0' COMMENT '浏览量',
  `publish_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发布时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `fk_news_category_idx` (`category_id`),
  KEY `idx_publish_time` (`publish_time` DESC),
  CONSTRAINT `fk_news_category` FOREIGN KEY (`category_id`) REFERENCES `news_category` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='新闻表';

CREATE TABLE IF NOT EXISTS `user` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '用户名',
  `password` varchar(255) NOT NULL COMMENT '密码（加密存储）',
  `nickname` varchar(50) DEFAULT NULL COMMENT '昵称',
  `avatar` varchar(255) DEFAULT NULL COMMENT '头像URL',
  `gender` enum('male','female','unknown') DEFAULT 'unknown' COMMENT '性别',
  `bio` varchar(500) DEFAULT NULL COMMENT '个人简介',
  `phone` varchar(20) DEFAULT NULL COMMENT '手机号',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username_UNIQUE` (`username`),
  UNIQUE KEY `phone_UNIQUE` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户信息表';

CREATE TABLE IF NOT EXISTS `user_token` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '令牌ID',
  `user_id` int unsigned NOT NULL COMMENT '用户ID',
  `token` varchar(255) NOT NULL COMMENT '令牌值',
  `expires_at` timestamp NOT NULL COMMENT '过期时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_UNIQUE` (`token`),
  KEY `fk_user_token_user_idx` (`user_id`),
  CONSTRAINT `fk_user_token_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户令牌表';

CREATE TABLE IF NOT EXISTS `favorite` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '收藏ID',
  `user_id` int unsigned NOT NULL COMMENT '用户ID',
  `news_id` int unsigned NOT NULL COMMENT '新闻ID',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_news_unique` (`user_id`,`news_id`),
  KEY `fk_favorite_user_idx` (`user_id`),
  KEY `fk_favorite_news_idx` (`news_id`),
  CONSTRAINT `fk_favorite_news` FOREIGN KEY (`news_id`) REFERENCES `news` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_favorite_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='收藏表';

CREATE TABLE IF NOT EXISTS `history` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '历史ID',
  `user_id` int unsigned NOT NULL COMMENT '用户ID',
  `news_id` int unsigned NOT NULL COMMENT '新闻ID',
  `view_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '浏览时间',
  PRIMARY KEY (`id`),
  KEY `fk_history_user_idx` (`user_id`),
  KEY `fk_history_news_idx` (`news_id`),
  KEY `idx_view_time` (`view_time` DESC),
  CONSTRAINT `fk_history_news` FOREIGN KEY (`news_id`) REFERENCES `news` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_history_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='浏览历史表';
