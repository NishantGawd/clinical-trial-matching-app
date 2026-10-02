import { MarketingNav } from "@/components/marketing/MarketingNav";
import { Hero } from "@/components/marketing/Hero";
import { FeatureGrid } from "@/components/marketing/FeatureGrid";
import { HowItWorks } from "@/components/marketing/HowItWorks";
import { TrustSection } from "@/components/marketing/TrustSection";
import { FinalCta } from "@/components/marketing/FinalCta";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <MarketingNav />
      <main className="flex-1">
        <Hero />
        <FeatureGrid />
        <HowItWorks />
        <TrustSection />
        <FinalCta />
      </main>
      <MarketingFooter />
    </div>
  );
}
