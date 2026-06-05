-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Config" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "key" TEXT NOT NULL,
    "val" TEXT NOT NULL,
    "remark" TEXT,
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME
);
INSERT INTO "new_Config" ("createdAt", "id", "key", "remark", "updatedAt", "val") SELECT "createdAt", "id", "key", "remark", "updatedAt", "val" FROM "Config";
DROP TABLE "Config";
ALTER TABLE "new_Config" RENAME TO "Config";
CREATE UNIQUE INDEX "Config_key_key" ON "Config"("key");
CREATE TABLE "new_CrawlResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "crawlerId" INTEGER NOT NULL,
    "successFlag" BOOLEAN NOT NULL,
    "message" TEXT,
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME,
    CONSTRAINT "CrawlResult_crawlerId_fkey" FOREIGN KEY ("crawlerId") REFERENCES "Crawler" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);
INSERT INTO "new_CrawlResult" ("crawlerId", "createdAt", "id", "message", "successFlag", "updatedAt") SELECT "crawlerId", "createdAt", "id", "message", "successFlag", "updatedAt" FROM "CrawlResult";
DROP TABLE "CrawlResult";
ALTER TABLE "new_CrawlResult" RENAME TO "CrawlResult";
CREATE TABLE "new_Crawler" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cmdPrefix" TEXT NOT NULL,
    "scriptPath" TEXT NOT NULL,
    "language" TEXT NOT NULL,
    "cron" TEXT NOT NULL DEFAULT '0 10 6 * * *',
    "disabled" BOOLEAN NOT NULL DEFAULT false,
    "remark" TEXT,
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME
);
INSERT INTO "new_Crawler" ("cmdPrefix", "createdAt", "disabled", "id", "language", "remark", "scriptPath", "updatedAt") SELECT "cmdPrefix", "createdAt", "disabled", "id", "language", "remark", "scriptPath", "updatedAt" FROM "Crawler";
DROP TABLE "Crawler";
ALTER TABLE "new_Crawler" RENAME TO "Crawler";
CREATE TABLE "new_LLMChatResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "newsIds" TEXT NOT NULL,
    "completionBody" TEXT NOT NULL,
    "message" TEXT,
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME
);
INSERT INTO "new_LLMChatResult" ("completionBody", "createdAt", "id", "message", "newsIds", "updatedAt") SELECT "completionBody", "createdAt", "id", "message", "newsIds", "updatedAt" FROM "LLMChatResult";
DROP TABLE "LLMChatResult";
ALTER TABLE "new_LLMChatResult" RENAME TO "LLMChatResult";
CREATE TABLE "new_News" (
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
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME
);
INSERT INTO "new_News" ("content", "contentMd5", "createdAt", "disabled", "id", "nature", "priority", "publishDateTime", "remark", "sourceUrl", "title", "updatedAt") SELECT "content", "contentMd5", "createdAt", "disabled", "id", "nature", "priority", "publishDateTime", "remark", "sourceUrl", "title", "updatedAt" FROM "News";
DROP TABLE "News";
ALTER TABLE "new_News" RENAME TO "News";
CREATE UNIQUE INDEX "News_contentMd5_key" ON "News"("contentMd5");
CREATE TABLE "new_PushResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "scheduleId" INTEGER NOT NULL,
    "content" TEXT NOT NULL,
    "to" TEXT NOT NULL,
    "resultCode" INTEGER NOT NULL,
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME,
    CONSTRAINT "PushResult_scheduleId_fkey" FOREIGN KEY ("scheduleId") REFERENCES "PushSchedule" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);
INSERT INTO "new_PushResult" ("content", "createdAt", "id", "resultCode", "scheduleId", "to", "updatedAt") SELECT "content", "createdAt", "id", "resultCode", "scheduleId", "to", "updatedAt" FROM "PushResult";
DROP TABLE "PushResult";
ALTER TABLE "new_PushResult" RENAME TO "PushResult";
CREATE TABLE "new_PushSchedule" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "cron" TEXT NOT NULL,
    "messageType" TEXT NOT NULL,
    "channel" TEXT NOT NULL,
    "to" TEXT NOT NULL,
    "disabled" BOOLEAN NOT NULL DEFAULT false,
    "remark" TEXT,
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME
);
INSERT INTO "new_PushSchedule" ("channel", "createdAt", "cron", "disabled", "id", "messageType", "remark", "to", "updatedAt") SELECT "channel", "createdAt", "cron", "disabled", "id", "messageType", "remark", "to", "updatedAt" FROM "PushSchedule";
DROP TABLE "PushSchedule";
ALTER TABLE "new_PushSchedule" RENAME TO "PushSchedule";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
