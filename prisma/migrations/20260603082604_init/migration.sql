-- CreateTable
CREATE TABLE "News" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "title" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "contentMd5" TEXT NOT NULL,
    "sourceUrl" TEXT NOT NULL,
    "disabled" BOOLEAN NOT NULL DEFAULT false,
    "publishDateTime" DATETIME NOT NULL,
    "remark" TEXT,
    "priority" INTEGER,
    "nature" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "Crawler" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cmdPrefix" TEXT NOT NULL,
    "scriptPath" TEXT NOT NULL,
    "language" TEXT NOT NULL,
    "disabled" BOOLEAN NOT NULL DEFAULT false,
    "remark" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "CrawlResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "crawlerId" INTEGER NOT NULL,
    "successFlag" BOOLEAN NOT NULL,
    "message" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "CrawlResult_crawlerId_fkey" FOREIGN KEY ("crawlerId") REFERENCES "Crawler" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "LLMChatResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "newsIds" TEXT NOT NULL,
    "completionBody" TEXT NOT NULL,
    "message" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "PushSchedule" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cron" TEXT NOT NULL,
    "messageType" TEXT NOT NULL,
    "channel" TEXT NOT NULL,
    "to" TEXT NOT NULL,
    "disabled" BOOLEAN NOT NULL DEFAULT false,
    "remark" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "PushResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "scheduleId" INTEGER NOT NULL,
    "content" TEXT NOT NULL,
    "to" TEXT NOT NULL,
    "resultCode" INTEGER NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "PushResult_scheduleId_fkey" FOREIGN KEY ("scheduleId") REFERENCES "PushSchedule" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Config" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "key" TEXT NOT NULL,
    "val" TEXT NOT NULL,
    "remark" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "News_contentMd5_key" ON "News"("contentMd5");

-- CreateIndex
CREATE UNIQUE INDEX "Config_key_key" ON "Config"("key");
