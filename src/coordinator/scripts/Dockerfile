FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
# --legacy-peer-deps: 0g-ts-sdk@0.3.3 pins peer ethers@6.13.1 but the
# project resolves to ^6.13.4 (currently 6.16.0). Local installs use this
# same flag, so match it here.
RUN npm install --legacy-peer-deps --no-audit --no-fund

COPY *.ts tsconfig.json ./

EXPOSE 8787 8788

# Default command runs the storage sidecar; compose overrides for headers sidecar.
CMD ["npx", "tsx", "storage_sidecar.ts"]
