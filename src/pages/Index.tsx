import Header from "@/components/Header";
import Hero from "@/components/Hero";
import LocationForm from "@/components/LocationForm";
import Footer from "@/components/Footer";

const Index = () => {
  return (
    <div className="min-h-screen bg-gradient-background">
      <Header />
      <Hero />
      
      {/* Main Form Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto max-w-2xl">
          <div className="text-center mb-8">
            <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-4">
              درخواست ارسال مرسوله
            </h2>
            <p className="text-muted-foreground text-base md:text-lg">
              مبدا و مقصد خود را انتخاب کنید تا کارشناس ما با شما تماس بگیرد
            </p>
          </div>
          
          <div className="flex justify-center">
            <LocationForm />
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Index;
