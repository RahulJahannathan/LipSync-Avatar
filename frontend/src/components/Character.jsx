"use client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function Character() {
  const tessaCostumes = [
    { id: 1, name: "Formal", image: "images/tessa_f_b.png", model: "tessa_formal_blue" },
    { id: 2, name: "Formal", image: "/images/tessa_f_br.png", model: "tessa_formal_brown" },
    { id: 3, name: "Formal", image: "/images/tessa_f_l.png", model: "tessa_formal_light" },
    { id: 4, name: "Semi-formal", image: "/images/tessa_b.png", model: "tessa_blue" },
    { id: 5, name: "Semi-formal", image: "/images/tessa_w.png", model: "tessa_white" },
    { id: 6, name: "Semi-formal", image: "/images/tessa_black.png", model: "tessa_black" },
  ]

  const hardinCostumes = [
    { id: 9, name: "Formal", image: "/images/hardin_f_blue.png?height=50&width=50", model: "hardin_formal_blue" },
    { id: 10, name: "Formal", image: "/images/hardin_f_brown.png", model: "hardin_formal_brown" },
    { id: 11, name: "Formal", image: "/images/hardin_f_black.png", model: "hardin_formal_black" },
    { id: 12, name: "Semi-formal", image: "/images/hardin_n.png", model: "hardin_navy" },
    { id: 13, name: "Semi-formal", image: "/images/hardin_w.png", model: "hardin_white" },
    { id: 14, name: "Semi-formal", image: "/images/hardin_black.png", model: "hardin_black" },
    { id: 15, name: "Semi-formal", image: "/images/hardin_b.png", model: "hardin_blue" },
  ]

  
    const handleCostumeClick = (character, costume) => {
    const selectedData = { character, ...costume }
    localStorage.setItem("selectedCostume", JSON.stringify(selectedData))
    window.dispatchEvent(new Event("costumeChange")) // 🔔 Notify listeners
    console.log("Selected costume saved:", selectedData)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Main Heading */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-4">Characters</h1>
          <p className="text-lg text-gray-600">Choose costumes for your favorite characters</p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Tessa Section */}
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-3xl font-semibold text-purple-700 mb-2">Tessa</h2>
              <div className="w-20 h-1 bg-purple-400 mx-auto rounded-full"></div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {tessaCostumes.map((costume) => (
                <Card
                  key={costume.id}
                  className="hover:shadow-lg transition-all duration-300 hover:scale-105 cursor-pointer border-purple-200 hover:border-purple-400"
                  onClick={() => handleCostumeClick("Tessa", costume)}
                >
                  <CardHeader className="pb-2">
                    <div className="aspect-[4/3] overflow-hidden rounded-md mb-2">
                      <img
                        src={costume.image || "/placeholder.svg"}
                        alt={costume.name}
                        className="w-full h-full object-cover transition-transform duration-300 hover:scale-110"
                      />
                    </div>
                    <CardTitle className="text-sm font-medium text-center text-purple-800">{costume.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <Button
                      variant="outline"
                      className="w-full border-purple-300 text-purple-700 hover:bg-purple-50 hover:border-purple-400 bg-transparent"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCostumeClick("Tessa", costume)
                      }}
                    >
                      Select Outfit
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Hardin Section */}
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-3xl font-semibold text-gray-700 mb-2">Hardin</h2>
              <div className="w-20 h-1 bg-gray-400 mx-auto rounded-full"></div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {hardinCostumes.map((costume) => (
                <Card
                  key={costume.id}
                  className="hover:shadow-lg transition-all duration-300 hover:scale-105 cursor-pointer border-gray-200 hover:border-gray-400"
                  onClick={() => handleCostumeClick("Hardin", costume)}
                >
                  <CardHeader className="pb-2">
                    <div className="aspect-[4/3] overflow-hidden rounded-md mb-3">
                      <img
                        src={costume.image || "/placeholder.svg"}
                        alt={costume.name}
                        className="w-full h-full object-cover transition-transform duration-300 hover:scale-110"
                      />
                    </div>
                    <CardTitle className="text-sm font-medium text-center text-gray-800">{costume.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <Button
                      variant="outline"
                      className="w-full border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400 bg-transparent"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCostumeClick("Hardin", costume)
                      }}
                    >
                      Select Outfit
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
