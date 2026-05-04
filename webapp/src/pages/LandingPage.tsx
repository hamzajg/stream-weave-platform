import { Navbar } from '../components/Navbar'
import { Hero } from '../components/Hero'
import { Features } from '../components/Features'
import { Stats } from '../components/Stats'
import { Community } from '../components/Community'
import { Footer } from '../components/Footer'

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background-primary text-text-primary font-body blueprint-grid">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <Stats />
        <Community />
      </main>
      <Footer />
    </div>
  )
}
