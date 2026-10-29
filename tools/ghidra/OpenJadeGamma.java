// Export bounded gamma math evidence without changing the saved program.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import java.nio.file.*;
public class OpenJadeGamma extends GhidraScript {
 public void run() throws Exception {
  if (!"6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new Exception("Hash mismatch");
  Path out=Paths.get(getScriptArgs()[0]);Files.createDirectory(out);
  DecompInterface dec=new DecompInterface();dec.openProgram(currentProgram);
  StringBuilder values=new StringBuilder();for(long address:new long[]{0x007beb90,0x007beba0,0x007bebb0,0x007bebe0,0x007bebf0})values.append(Long.toHexString(address)).append(" double=").append(Double.longBitsToDouble(getLong(toAddr(address)))).append("\n");Files.writeString(out.resolve("constants.txt"),values.toString());
  try {for(long address:new long[]{0x0072a190,0x007348f8,0x00726df4}) {
   var f=getFunctionAt(toAddr(address));if(f==null)throw new Exception("Missing function");
   var r=dec.decompileFunction(f,60,monitor);if(r.decompileCompleted())Files.writeString(out.resolve(Long.toHexString(address)+".c"),r.getDecompiledFunction().getC());
   StringBuilder asm=new StringBuilder();var it=currentProgram.getListing().getInstructions(f.getBody(),true);while(it.hasNext()){var i=it.next();asm.append(i.getAddress()).append(" ").append(i).append("\n");}Files.writeString(out.resolve(Long.toHexString(address)+".txt"),asm.toString());
  }}finally{dec.dispose();}
 }
}
