export default function DocumentListComponent() {
  const handleDelete = async (filename) => {

    await callAction({
      name: "delete_file",
      payload: {
        filename: filename
      }
    });
  };

  return (
    <div class="grid grid-cols-1 gap-4">
      {props.filenames.length === 0 && <div class="text-sm"> No files found </div>}
      {props.filenames.map((filename, index) => (
        <div key={index} class="grid grid-flow-col grid-rows-2">
          <div class="text-sm">
            {filename}
          </div>
          <div>
            <button 
              class="bg-red-500 text-white text-xs px-3 py-1 rounded hover:bg-red-600"
              onClick={() => handleDelete(filename)}
            > 
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
