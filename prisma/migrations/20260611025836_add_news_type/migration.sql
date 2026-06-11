-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
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
    "newsType" TEXT NOT NULL DEFAULT 'Rolling',
    "createdAt" DATETIME DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME
);
INSERT INTO "new_News" ("content", "contentMd5", "createdAt", "disabled", "id", "nature", "priority", "publishDateTime", "remark", "sourceUrl", "title", "updatedAt") SELECT "content", "contentMd5", "createdAt", "disabled", "id", "nature", "priority", "publishDateTime", "remark", "sourceUrl", "title", "updatedAt" FROM "News";
DROP TABLE "News";
ALTER TABLE "new_News" RENAME TO "News";
CREATE UNIQUE INDEX "News_contentMd5_key" ON "News"("contentMd5");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
