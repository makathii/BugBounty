FROM node:25-alpine
LABEL authors="kathi"

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy project files
COPY . .

# Expose port
EXPOSE 3000

# Start the development server
CMD ["npm", "start"]