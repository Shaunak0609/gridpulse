import { useParams } from 'react-router-dom'

export default function DriverDetail() {
  const { id } = useParams()

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">Driver Profile</h1>
      <p className="text-gray-400 mb-8">Driver ID: {id}</p>
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-12 text-center text-gray-500">
        Driver details coming soon.
      </div>
    </div>
  )
}
