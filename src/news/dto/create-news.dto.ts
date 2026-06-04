export type CreateNewsDto = {
  title: string;
  content: string;
  sourceUrl: string;
  disabled?: boolean;
  publishDateTime: Date | string;
  remark?: string | null;
};
