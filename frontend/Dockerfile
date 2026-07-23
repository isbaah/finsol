FROM node:24-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./

# ---------------------------------------------------------------------------
# dev: used by docker-compose for local development (hot reload via bind mount)
# ---------------------------------------------------------------------------
FROM base AS dev
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ---------------------------------------------------------------------------
# deps: production dependency install, isolated so it can be cached
# ---------------------------------------------------------------------------
FROM base AS deps
RUN npm ci

# ---------------------------------------------------------------------------
# builder: production build
# ---------------------------------------------------------------------------
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# runner: minimal production image
# ---------------------------------------------------------------------------
FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
