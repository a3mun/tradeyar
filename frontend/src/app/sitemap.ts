
import type { MetadataRoute } from "next";

const SITE_URL = "https://trademun.ir";

/**
 * فقط مسیرهای عمومی و قابل مشاهده بدون ورود را در Sitemap قرار دهید.
 * اگر مسیر یا slug عمومی جدیدی اضافه شد، آن را اینجا هم اضافه کنید.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: SITE_URL,
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${SITE_URL}/login`,
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${SITE_URL}/about`,
      changeFrequency: "monthly",
      priority: 0.6,
    },
    {
      url: `${SITE_URL}/contact`,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${SITE_URL}/faq`,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${SITE_URL}/subscription`,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/extension/guide`,
      changeFrequency: "monthly",
      priority: 0.8,
    },
  ];
}
