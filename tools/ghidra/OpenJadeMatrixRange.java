// Export existing functions in a bounded graphics region for matrix tracing.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import java.nio.file.*;
public class OpenJadeMatrixRange extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  Path out=Paths.get(getScriptArgs()[0]);Files.createDirectory(out);
  var dec=new DecompInterface();dec.openProgram(currentProgram);
  try {var fs=currentProgram.getFunctionManager().getFunctions(toAddr(0x00667a00L),true);
   while(fs.hasNext()){var f=fs.next();if(f.getEntryPoint().getOffset()>0x00668700L)break;
    var r=dec.decompileFunction(f,30,monitor);if(r.decompileCompleted())Files.writeString(out.resolve(f.getEntryPoint()+".c"),r.getDecompiledFunction().getC());
   }
  }finally{dec.dispose();}
 }
}
