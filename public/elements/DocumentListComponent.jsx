export default function DocumentListComponent() {
  const handleDelete = async (doc) => {

    await callAction({
      name: "delete_file",
      payload: {
        file_path: doc
      }
    });
  };

  return (
    <div className="p-4">
      <h3 className="text-lg font-bold mb-2">Uploaded Documents</h3>
      <ul className="list-disc pl-5">
        {props.documents.length === 0 && <li>No documents found</li>}
        {props.documents.map((doc, index) => (
          <li key={index} className="flex items-center justify-between bg-gray-100 p-2 rounded">
            <span className="text-sm">{doc.split('/').pop()}</span>
            <button

              onClick={() => handleDelete(doc)}
              className="bg-red-500 text-white text-xs px-3 py-1 rounded hover:bg-red-600"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
