FROM oven/bun:1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends npm \
    && rm -rf /var/lib/apt/lists/*

COPY package.json bun.lock ./

RUN bun install --frozen-lockfile

COPY . .

EXPOSE 3000

CMD ["bun", "run", "dev", "--", "-H", "0.0.0.0"]
