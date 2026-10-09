FROM node:18-alpine
LABEL authors="kathi"

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
# --legacy-peer-deps: react-scripts 5.0.1 has peer dep conflicts with React 19
RUN npm install --legacy-peer-deps

# Copy project files
COPY . .

# Expose port
EXPOSE 3000

# Start the development server
# NODE_OPTIONS: react-scripts 5.0.1 needs legacy OpenSSL provider on Node 17+
ENV NODE_OPTIONS=--openssl-legacy-provider
CMD ["npm", "start"]