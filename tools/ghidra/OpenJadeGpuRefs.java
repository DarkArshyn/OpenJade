// Inspect selected data references and their containing functions, read-only.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.nio.file.*;
import java.util.*;
public class OpenJadeGpuRefs extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  String[] args=getScriptArgs(); Path out=Paths.get(args[0]); Files.createDirectory(out);
  DecompInterface dec=new DecompInterface(); dec.openProgram(currentProgram);
  Set<Function> functions=new HashSet<>(); StringBuilder log=new StringBuilder();
  try {for(int i=1;i<args.length;i++){
   var address=toAddr(Long.parseUnsignedLong(args[i],16));
   log.append(address).append(" word=").append(Integer.toHexString(getInt(address))).append("\n");
   var refs=currentProgram.getReferenceManager().getReferencesTo(address);
   while(refs.hasNext()){var ref=refs.next();var f=getFunctionContaining(ref.getFromAddress());log.append(ref).append(" function=").append(f).append("\n");if(f!=null)functions.add(f);}
  }
  for(Function f:functions){var result=dec.decompileFunction(f,60,monitor);if(result.decompileCompleted())Files.writeString(out.resolve(f.getEntryPoint()+".c"),result.getDecompiledFunction().getC());}
  Files.writeString(out.resolve("references.txt"),log.toString());
  } finally {dec.dispose();}
 }
}
