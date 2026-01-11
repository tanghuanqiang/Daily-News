# 构建阶段
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 构建参数（用于传递环境变量）
ARG VITE_API_URL=http://localhost:8000

# 设置环境变量（Vite需要）
ENV VITE_API_URL=$VITE_API_URL

# 复制package文件
COPY package.json pnpm-lock.yaml* package-lock.json* yarn.lock* ./

# 安装依赖（优先使用pnpm，如果不存在则使用npm）
RUN if [ -f pnpm-lock.yaml ]; then \
        npm install -g pnpm && pnpm install; \
    elif [ -f yarn.lock ]; then \
        npm install -g yarn && yarn install; \
    else \
        npm install; \
    fi

# 复制源代码
COPY . .

# 构建应用
RUN if [ -f pnpm-lock.yaml ]; then \
        pnpm run build; \
    elif [ -f yarn.lock ]; then \
        yarn build; \
    else \
        npm run build; \
    fi

# 生产阶段
FROM nginx:alpine

# 复制构建产物到nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]
