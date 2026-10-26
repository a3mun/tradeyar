# ═══════════════════════════════════════════════════════════
# Trademun — Frontend Dockerfile (Next.js Standalone)
# ═══════════════════════════════════════════════════════════

# ─── Stage 1: Dependencies ───
FROM node:20-alpine AS deps

# ⬅️ تغییر mirror به علی‌بابا (dl-cdn در ایران جواب نمی‌ده — TLS error)
RUN sed -i 's|dl-cdn.alpinelinux.org|mirrors.aliyun.com|g' /etc/apk/repositories

# ⬅️ نصب libc6-compat (فقط یک بار)
RUN apk add --no-cache libc6-compat

WORKDIR /app
COPY package.json package-lock.json* ./

# ⬅️ mirror npm به پارس‌پک (سریع‌تر از npmmirror روی سرور شما)
RUN npm config set registry https://mirror.abrha.net/repository/npm/ \
 && npm ci --prefer-offline --no-audit \
    --fetch-retries=5 \
    --fetch-retry-mintimeout=20000 \
    --fetch-retry-maxtimeout=120000

# ─── Stage 2: Builder ───
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max-old-space-size=768"

RUN npm run build

# ─── Stage 3: Runner (Standalone) ───
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# ─── کپی فایل‌های standalone ───
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]